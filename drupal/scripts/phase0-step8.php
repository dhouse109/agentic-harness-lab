<?php

declare(strict_types=1);

/**
 * Phase 0, Step 8: create the alt-text suggestion review queue structure.
 *
 * Run from the Drupal project root:
 *
 *   ddev drush php:script scripts/phase0-step8.php -- apply
 *   ddev drush php:script scripts/phase0-step8.php -- audit
 *   ddev drush php:script scripts/phase0-step8.php -- migrate-test-source
 *   ddev drush php:script scripts/phase0-step8.php -- remove confirm
 *
 * The script is idempotent. It refuses to silently replace incompatible field
 * storage because changing a field type or target entity type can destroy data.
 */

use Drupal\Core\Field\Entity\BaseFieldOverride;
use Drupal\field\Entity\FieldConfig;
use Drupal\field\Entity\FieldStorageConfig;
use Drupal\node\NodeTypeInterface;
use Drupal\views\Entity\View;

const STEP8_BUNDLE = 'alt_text_suggestion';
const STEP8_VIEW_ID = 'alt_text_review_queue';
const STEP8_VIEW_PATH = 'admin/review-queue';
const STEP8_SCRIPT_VERSION = '3.1.0';

$script_args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $script_args[0] ?? 'apply';
$confirmation = $script_args[1] ?? '';

if (!in_array($mode, ['apply', 'audit', 'migrate-test-source', 'remove'], TRUE)) {
  step8_fail(sprintf(
    'Unknown mode "%s". Use one of: apply, audit, migrate-test-source, remove.',
    $mode,
  ));
}

if ($mode === 'remove' && $confirmation !== 'confirm') {
  step8_fail('Removal is destructive. Run again as: remove confirm');
}

step8_require_environment();
step8_note('Step 8 script version: ' . STEP8_SCRIPT_VERSION);

if ($mode === 'audit') {
  step8_audit();
  return;
}

if ($mode === 'remove') {
  step8_remove();
  return;
}

step8_ensure_article_prerequisites();
step8_migrate_source_framework_storage();
step8_preflight_compatibility();
step8_ensure_content_type();
step8_ensure_base_field_overrides();
step8_ensure_fields();
step8_ensure_displays();
step8_ensure_review_queue_view();

step8_ok($mode === 'migrate-test-source'
  ? 'Phase 0 Step 8 provenance migration completed.'
  : 'Phase 0 Step 8 apply mode completed.');
step8_audit();
step8_note('Next: run ./scripts/run-phase0-step7.sh finalize');
step8_note('Then export configuration with: ddev drush cex -y');

/**
 * Defines the complete field model from the final Phase 0 runbook.
 *
 * @return array<string, array<string, mixed>>
 */
function step8_field_definitions(): array {
  return [
    'field_target_node' => [
      'label' => 'Target article',
      'description' => 'The Article entity containing the image-field usage.',
      'type' => 'entity_reference',
      'storage_settings' => ['target_type' => 'node'],
      'required' => TRUE,
      'field_settings' => [
        'handler' => 'default:node',
        'handler_settings' => [
          'target_bundles' => ['article' => 'article'],
          'sort' => ['field' => '_none', 'direction' => 'ASC'],
          'auto_create' => FALSE,
          'auto_create_bundle' => '',
        ],
      ],
      'form' => ['type' => 'entity_reference_autocomplete'],
      'view' => [
        'type' => 'entity_reference_label',
        'settings' => ['link' => TRUE],
      ],
    ],
    'field_target_revision' => [
      'label' => 'Target revision',
      'description' => 'The exact Article revision inspected by the framework.',
      'type' => 'integer',
      'storage_settings' => ['unsigned' => TRUE, 'size' => 'normal'],
      'required' => TRUE,
      'field_settings' => ['min' => 1, 'max' => NULL, 'prefix' => '', 'suffix' => ''],
      'form' => ['type' => 'number'],
      'view' => [
        'type' => 'number_integer',
        'settings' => ['thousand_separator' => '', 'prefix_suffix' => TRUE],
      ],
    ],
    'field_target_field' => [
      'label' => 'Target field',
      'description' => 'The Drupal image field machine name.',
      'type' => 'string',
      'storage_settings' => ['max_length' => 64, 'case_sensitive' => FALSE, 'is_ascii' => TRUE],
      'required' => TRUE,
      'field_settings' => [],
      'form' => ['type' => 'string_textfield'],
      'view' => ['type' => 'string', 'settings' => ['link_to_entity' => FALSE]],
    ],
    'field_target_delta' => [
      'label' => 'Target delta',
      'description' => 'The zero-based position inside the multivalue image field.',
      'type' => 'integer',
      'storage_settings' => ['unsigned' => TRUE, 'size' => 'normal'],
      'required' => TRUE,
      'field_settings' => ['min' => 0, 'max' => NULL, 'prefix' => '', 'suffix' => ''],
      'form' => ['type' => 'number'],
      'view' => [
        'type' => 'number_integer',
        'settings' => ['thousand_separator' => '', 'prefix_suffix' => TRUE],
      ],
    ],
    'field_target_file' => [
      'label' => 'Target file',
      'description' => 'The exact File entity referenced by the Article image-field item.',
      'type' => 'entity_reference',
      'storage_settings' => ['target_type' => 'file'],
      'required' => TRUE,
      'field_settings' => [
        'handler' => 'default:file',
        'handler_settings' => [],
      ],
      'form' => ['type' => 'entity_reference_autocomplete'],
      'view' => [
        'type' => 'entity_reference_label',
        'settings' => ['link' => FALSE],
      ],
    ],
    'field_proposed_alt' => [
      'label' => 'Proposed alt text',
      'description' => 'An editable recommendation. Saving a reviewer change creates a new revision.',
      'type' => 'string_long',
      'storage_settings' => ['case_sensitive' => FALSE],
      'required' => TRUE,
      'field_settings' => [],
      'form' => [
        'type' => 'string_textarea',
        'settings' => ['rows' => 4, 'placeholder' => 'Describe the image in its page context.'],
      ],
      'view' => ['type' => 'basic_string', 'settings' => []],
    ],
    'field_review_status' => [
      'label' => 'Review status',
      'description' => 'The explicit human decision for this recommendation.',
      'type' => 'list_string',
      'storage_settings' => [
        'allowed_values' => [
          'pending' => 'Pending',
          'approved' => 'Approved',
          'rejected' => 'Rejected',
        ],
        'allowed_values_function' => '',
      ],
      'required' => TRUE,
      'field_settings' => [],
      'default_value' => [['value' => 'pending']],
      'form' => ['type' => 'options_select'],
      'view' => ['type' => 'list_default', 'settings' => []],
    ],
    'field_source_framework' => [
      'label' => 'Source framework',
      'description' => 'The implementation or controlled test fixture that generated the recommendation.',
      'type' => 'list_string',
      'storage_settings' => [
        'allowed_values' => [
          'phase0_fixture' => 'Phase 0 test fixture',
          'drupal_ai' => 'Drupal AI',
          'langgraph' => 'LangGraph',
          'crewai' => 'CrewAI',
        ],
        'allowed_values_function' => '',
      ],
      'required' => TRUE,
      'field_settings' => [],
      'form' => ['type' => 'options_select'],
      'view' => ['type' => 'list_default', 'settings' => []],
    ],
    'field_run_id' => [
      'label' => 'Run ID',
      'description' => 'Links the recommendation to its execution logs and evidence.',
      'type' => 'string',
      'storage_settings' => ['max_length' => 128, 'case_sensitive' => TRUE, 'is_ascii' => TRUE],
      'required' => TRUE,
      'field_settings' => [],
      'form' => ['type' => 'string_textfield'],
      'view' => ['type' => 'string', 'settings' => ['link_to_entity' => FALSE]],
    ],
    'field_evidence_hash' => [
      'label' => 'Evidence hash',
      'description' => 'Optional hash linking to sanitized context evidence without storing secrets.',
      'type' => 'string',
      'storage_settings' => ['max_length' => 128, 'case_sensitive' => TRUE, 'is_ascii' => TRUE],
      'required' => FALSE,
      'field_settings' => [],
      'form' => ['type' => 'string_textfield'],
      'view' => ['type' => 'string', 'settings' => ['link_to_entity' => FALSE]],
    ],
  ];
}

/**
 * Verifies the core modules required by Step 8.
 *
 * The shell runner enables image and text before invoking this file. Keeping
 * the check here also makes direct php:script execution fail with a useful
 * message instead of a field-plugin exception.
 */
function step8_require_environment(): void {
  $module_handler = \Drupal::moduleHandler();
  $required_modules = ['node', 'field', 'file', 'image', 'text', 'options', 'views'];
  $missing = array_values(array_filter(
    $required_modules,
    static fn(string $module): bool => !$module_handler->moduleExists($module),
  ));

  if ($missing !== []) {
    step8_fail(sprintf(
      'Required modules are not enabled: %s. Run: ddev drush en -y image text',
      implode(', ', $missing),
    ));
  }

  if (!\Drupal::entityTypeManager()->getStorage('user_role')->load('content_editor')) {
    step8_warn('The content_editor role does not exist yet. Step 8 can run, but complete Step 7 before testing the queue.');
  }
}

/**
 * Creates the minimal Article structure required by the deterministic dataset.
 *
 * This intentionally does not recreate every Standard-profile feature. It
 * creates only the Article bundle, Body, and a two-value image field needed by
 * the Phase 0 experiment. Alt text is optional so Step 9 can seed controlled
 * missing-alt cases.
 */
function step8_ensure_article_prerequisites(): void {
  $type_storage = \Drupal::entityTypeManager()->getStorage('node_type');
  /** @var \Drupal\node\NodeTypeInterface|null $article */
  $article = $type_storage->load('article');

  if ($article === NULL) {
    $article = $type_storage->create([
      'name' => 'Article',
      'type' => 'article',
      'description' => 'Article content used by the Phase 0 agentic-harness lab.',
      'help' => NULL,
      'new_revision' => TRUE,
      'preview_mode' => 1,
      'display_submitted' => TRUE,
    ]);
    $article->save();
    step8_ok('Created prerequisite content type: Article (article).');
  }
  else {
    $article->set('new_revision', TRUE);
    $article->save();
    step8_note('Article content type already exists; ensured revisions are enabled.');
  }

  // Body field. Drupal normally provides node.body storage, but minimal or
  // custom installations are allowed to omit the Article bundle attachment.
  $body_storage = FieldStorageConfig::loadByName('node', 'body');
  if ($body_storage === NULL) {
    $body_storage = FieldStorageConfig::create([
      'field_name' => 'body',
      'entity_type' => 'node',
      'type' => 'text_long',
      'cardinality' => 1,
      'persist_with_no_fields' => TRUE,
      'translatable' => TRUE,
    ]);
    $body_storage->save();
    step8_ok('Created prerequisite field storage: node.body.');
  }
  elseif ($body_storage->getType() !== 'text_long') {
    step8_fail(sprintf(
      'Existing node.body field type is "%s"; expected "text_long". No Article fields were replaced.',
      $body_storage->getType(),
    ));
  }

  $body = FieldConfig::loadByName('node', 'article', 'body');
  if ($body === NULL) {
    $body = FieldConfig::create([
      'field_storage' => $body_storage,
      'bundle' => 'article',
      'label' => 'Body',
      'description' => '',
      'required' => FALSE,
      'translatable' => TRUE,
      'settings' => ['allowed_formats' => []],
    ]);
    $body->save();
    step8_ok('Attached Body to Article.');
  }

  // Image field. Two values are required because the Step 9 fixture includes
  // Articles with one or two image usages.
  $image_storage = FieldStorageConfig::loadByName('node', 'field_image');
  if ($image_storage === NULL) {
    $image_storage = FieldStorageConfig::create([
      'field_name' => 'field_image',
      'entity_type' => 'node',
      'type' => 'image',
      'cardinality' => 2,
      'translatable' => TRUE,
      'settings' => [
        'target_type' => 'file',
        'display_field' => FALSE,
        'display_default' => FALSE,
        'uri_scheme' => 'public',
        'default_image' => [
          'uuid' => NULL,
          'alt' => '',
          'title' => '',
          'width' => NULL,
          'height' => NULL,
        ],
      ],
    ]);
    $image_storage->save();
    step8_ok('Created prerequisite image storage: node.field_image (cardinality 2).');
  }
  else {
    if ($image_storage->getType() !== 'image') {
      step8_fail(sprintf(
        'Existing node.field_image field type is "%s"; expected "image". No field was replaced.',
        $image_storage->getType(),
      ));
    }
    $cardinality = $image_storage->getCardinality();
    if ($cardinality !== -1 && $cardinality < 2) {
      $image_storage->setCardinality(2);
      $image_storage->save();
      step8_ok('Expanded node.field_image cardinality to 2.');
    }
  }

  $image = FieldConfig::loadByName('node', 'article', 'field_image');
  $image_settings = [
    'handler' => 'default:file',
    'handler_settings' => [],
    'file_directory' => '[date:custom:Y]-[date:custom:m]',
    'file_extensions' => 'png gif jpg jpeg webp',
    'max_filesize' => '',
    'max_resolution' => '',
    'min_resolution' => '',
    'alt_field' => TRUE,
    'alt_field_required' => FALSE,
    'title_field' => FALSE,
    'title_field_required' => FALSE,
    'default_image' => [
      'uuid' => NULL,
      'alt' => '',
      'title' => '',
      'width' => NULL,
      'height' => NULL,
    ],
  ];

  if ($image === NULL) {
    $image = FieldConfig::create([
      'field_storage' => $image_storage,
      'bundle' => 'article',
      'label' => 'Image',
      'description' => 'One or two images used by the deterministic Phase 0 fixture.',
      'required' => FALSE,
      'translatable' => TRUE,
      'settings' => $image_settings,
    ]);
    $image->save();
    step8_ok('Attached field_image to Article with optional alt text.');
  }
  else {
    $image->setRequired(FALSE);
    $image->setSettings($image_settings);
    $image->save();
    step8_note('Article field_image already exists; ensured optional alt text and lab settings.');
  }

  $repository = \Drupal::service('entity_display.repository');
  $repository->getFormDisplay('node', 'article', 'default')
    ->setComponent('title', [
      'type' => 'string_textfield',
      'weight' => -20,
      'region' => 'content',
    ])
    ->setComponent('body', [
      'type' => 'text_textarea',
      'weight' => 0,
      'region' => 'content',
    ])
    ->setComponent('field_image', [
      'type' => 'image_image',
      'weight' => 10,
      'region' => 'content',
      'settings' => [
        'progress_indicator' => 'throbber',
        'preview_image_style' => 'thumbnail',
      ],
    ])
    ->save();

  $repository->getViewDisplay('node', 'article', 'default')
    ->setComponent('body', [
      'label' => 'hidden',
      'type' => 'text_default',
      'weight' => 0,
      'region' => 'content',
    ])
    ->setComponent('field_image', [
      'label' => 'hidden',
      'type' => 'image',
      'weight' => -1,
      'region' => 'content',
      'settings' => [
        'image_link' => '',
        'image_style' => '',
        'image_loading' => ['attribute' => 'lazy'],
      ],
    ])
    ->save();

  step8_ok('Article prerequisite structure is ready.');
}

/**
 * Safely adds the neutral Phase 0 fixture origin to the source list.
 *
 * This is an additive allowed-value migration. It accepts only the exact
 * legacy three-framework list or the corrected four-origin list. Any custom
 * or unknown list is rejected so this script cannot silently rewrite local
 * provenance semantics.
 */
function step8_migrate_source_framework_storage(): void {
  $storage = FieldStorageConfig::loadByName('node', 'field_source_framework');
  if ($storage === NULL) {
    step8_note('field_source_framework storage does not exist yet; apply will create it with the corrected origin list.');
    return;
  }

  if ($storage->getType() !== 'list_string') {
    step8_fail(sprintf(
      'Existing node.field_source_framework has type "%s"; expected list_string. No changes were made.',
      $storage->getType(),
    ));
  }

  $legacy = [
    'drupal_ai' => 'Drupal AI',
    'langgraph' => 'LangGraph',
    'crewai' => 'CrewAI',
  ];
  $corrected = step8_field_definitions()['field_source_framework']['storage_settings']['allowed_values'];
  $current = $storage->getSetting('allowed_values');

  if ($current === $corrected) {
    step8_ok('Source-origin list already includes the neutral Phase 0 test fixture.');
    return;
  }

  if ($current !== $legacy) {
    step8_fail(sprintf(
      'node.field_source_framework has an unexpected allowed-value list. Expected the exact legacy or corrected list; found %s. No changes were made.',
      var_export($current, TRUE),
    ));
  }

  $used_values = [];
  $node_storage = \Drupal::entityTypeManager()->getStorage('node');
  $suggestion_ids = $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP8_BUNDLE)
    ->execute();
  foreach ($node_storage->loadMultiple($suggestion_ids) as $suggestion) {
    foreach ($suggestion->get('field_source_framework') as $item) {
      $value = (string) $item->value;
      if ($value !== '') {
        $used_values[$value] = $value;
      }
    }
  }
  $unknown = array_values(array_diff(array_values($used_values), array_keys($legacy)));
  if ($unknown !== []) {
    step8_fail(sprintf(
      'Existing suggestions contain unknown source values: %s. No changes were made.',
      implode(', ', $unknown),
    ));
  }

  $storage->setSetting('allowed_values', $corrected);
  $storage->setSetting('allowed_values_function', '');
  $storage->save();
  step8_ok('Added phase0_fixture to node.field_source_framework without changing existing suggestion values.');
}

/**
 * Refuses to proceed when an existing storage has an incompatible schema.
 */
function step8_preflight_compatibility(): void {
  foreach (step8_field_definitions() as $field_name => $definition) {
    $storage = FieldStorageConfig::loadByName('node', $field_name);
    if ($storage === NULL) {
      continue;
    }

    if ($storage->getType() !== $definition['type']) {
      step8_fail(sprintf(
        'Existing field storage node.%s has type "%s"; expected "%s". No changes were made.',
        $field_name,
        $storage->getType(),
        $definition['type'],
      ));
    }

    if ($storage->getCardinality() !== 1) {
      step8_fail(sprintf(
        'Existing field storage node.%s has cardinality %d; expected 1. No changes were made.',
        $field_name,
        $storage->getCardinality(),
      ));
    }

    foreach ($definition['storage_settings'] as $key => $expected) {
      $actual = $storage->getSetting($key);
      if ($actual !== $expected) {
        step8_fail(sprintf(
          'Existing field storage node.%s setting "%s" is incompatible. Expected %s; found %s. No changes were made.',
          $field_name,
          $key,
          var_export($expected, TRUE),
          var_export($actual, TRUE),
        ));
      }
    }
  }

  step8_ok('Existing field storage, if any, is schema-compatible.');
}

/**
 * Creates or normalizes the suggestion node type.
 */
function step8_ensure_content_type(): void {
  $storage = \Drupal::entityTypeManager()->getStorage('node_type');
  /** @var \Drupal\node\NodeTypeInterface|null $type */
  $type = $storage->load(STEP8_BUNDLE);

  $values = [
    'name' => 'Alt text suggestion',
    'type' => STEP8_BUNDLE,
    'description' => 'Reviewable, revisioned alt-text recommendations produced by harness implementations or controlled lab fixtures.',
    'help' => 'Review the target provenance, edit the proposed alt text when needed, and record an explicit approval or rejection.',
    'new_revision' => TRUE,
    'preview_mode' => 0,
    'display_submitted' => FALSE,
  ];

  if ($type === NULL) {
    /** @var \Drupal\node\NodeTypeInterface $type */
    $type = $storage->create($values);
    $type->save();
    step8_ok('Created content type: Alt text suggestion (alt_text_suggestion).');
    return;
  }

  foreach ($values as $property => $value) {
    $type->set($property, $value);
  }
  $type->save();
  step8_note('Content type already existed; normalized its label, help text, and revision settings.');
}

/**
 * Configures the title and publication defaults for this lab bundle.
 */
function step8_ensure_base_field_overrides(): void {
  $base_fields = \Drupal::service('entity_field.manager')->getBaseFieldDefinitions('node');

  $title = BaseFieldOverride::loadByName('node', STEP8_BUNDLE, 'title');
  if ($title === NULL) {
    $title = BaseFieldOverride::createFromBaseFieldDefinition($base_fields['title'], STEP8_BUNDLE);
  }
  $title->setLabel('Suggestion title');
  $title->setDescription('Use a concise identifier such as "Article 12 / field_image / delta 0".');
  $title->setRequired(TRUE);
  $title->save();

  // Drupal core has no bundle-specific "view any unpublished" permission.
  // This dummy-data lab therefore keeps suggestion records published by
  // default while protecting the administrative queue with a permission.
  // The agent still receives no edit, approve, reject, or delete permission.
  $status = BaseFieldOverride::loadByName('node', STEP8_BUNDLE, 'status');
  if ($status === NULL) {
    $status = BaseFieldOverride::createFromBaseFieldDefinition($base_fields['status'], STEP8_BUNDLE);
  }
  $status->setDefaultValue([['value' => 1]]);
  $status->save();

  step8_ok('Configured title and published-by-default lab behavior.');
}

/**
 * Creates or updates all field storage and bundle field configuration.
 */
function step8_ensure_fields(): void {
  foreach (step8_field_definitions() as $field_name => $definition) {
    $storage = FieldStorageConfig::loadByName('node', $field_name);
    if ($storage === NULL) {
      $storage = FieldStorageConfig::create([
        'field_name' => $field_name,
        'entity_type' => 'node',
        'type' => $definition['type'],
        'cardinality' => 1,
        'settings' => $definition['storage_settings'],
        'translatable' => FALSE,
      ]);
      $storage->save();
      step8_ok(sprintf('Created field storage: node.%s', $field_name));
    }

    $field = FieldConfig::loadByName('node', STEP8_BUNDLE, $field_name);
    $values = [
      'field_name' => $field_name,
      'entity_type' => 'node',
      'bundle' => STEP8_BUNDLE,
      'label' => $definition['label'],
      'description' => $definition['description'],
      'required' => $definition['required'],
      'translatable' => FALSE,
      'settings' => $definition['field_settings'],
      'default_value' => $definition['default_value'] ?? [],
    ];

    if ($field === NULL) {
      $field = FieldConfig::create($values);
      $field->save();
      step8_ok(sprintf('Attached field: %s', $field_name));
      continue;
    }

    $field->setLabel($definition['label']);
    $field->setDescription($definition['description']);
    $field->setRequired($definition['required']);
    $field->setTranslatable(FALSE);
    $field->setSettings($definition['field_settings']);
    $field->setDefaultValue($definition['default_value'] ?? []);
    $field->save();
    step8_note(sprintf('Field already existed; normalized bundle settings: %s', $field_name));
  }
}

/**
 * Configures the reviewer edit form and a useful default entity display.
 */
function step8_ensure_displays(): void {
  $repository = \Drupal::service('entity_display.repository');
  $form_display = $repository->getFormDisplay('node', STEP8_BUNDLE, 'default');

  $form_display->setComponent('title', [
    'type' => 'string_textfield',
    'weight' => -20,
    'region' => 'content',
    'settings' => ['size' => 60, 'placeholder' => 'Article / field / delta'],
  ]);

  $weight = -10;
  foreach (step8_field_definitions() as $field_name => $definition) {
    $form_display->setComponent($field_name, [
      'type' => $definition['form']['type'],
      'weight' => $weight,
      'region' => 'content',
      'settings' => $definition['form']['settings'] ?? [],
      'third_party_settings' => [],
    ]);
    $weight += 10;
  }

  // Keep publication controls out of the reviewer workflow. Suggestion nodes
  // are published by default in this dummy-data lab; the review decision is
  // field_review_status, not Drupal's publication status.
  foreach (['status', 'promote', 'sticky', 'path', 'uid', 'created'] as $hidden) {
    $form_display->removeComponent($hidden);
  }
  $form_display->save();

  $view_display = $repository->getViewDisplay('node', STEP8_BUNDLE, 'default');
  $weight = 0;
  foreach (step8_field_definitions() as $field_name => $definition) {
    $view_display->setComponent($field_name, [
      'label' => 'above',
      'type' => $definition['view']['type'],
      'weight' => $weight,
      'region' => 'content',
      'settings' => $definition['view']['settings'] ?? [],
      'third_party_settings' => [],
    ]);
    $weight += 10;
  }
  $view_display->removeComponent('links');
  $view_display->save();

  step8_ok('Configured reviewer form and default entity display.');
}

/**
 * Creates or replaces the named review-queue View configuration.
 */
function step8_ensure_review_queue_view(): void {
  $fields = [
    'title' => step8_view_base_field(
      'title',
      'node_field_data',
      'Suggestion',
      'string',
      ['link_to_entity' => TRUE],
    ),
    'field_target_node' => step8_view_config_field(
      'field_target_node',
      'Article',
      'entity_reference_label',
      ['link' => TRUE],
      'target_id',
    ),
    'field_target_revision' => step8_view_config_field(
      'field_target_revision',
      'Rev',
      'number_integer',
      ['thousand_separator' => '', 'prefix_suffix' => TRUE],
      'value',
    ),
    'field_target_field' => step8_view_config_field(
      'field_target_field',
      'Field',
      'string',
      ['link_to_entity' => FALSE],
      'value',
    ),
    'field_target_delta' => step8_view_config_field(
      'field_target_delta',
      'Delta',
      'number_integer',
      ['thousand_separator' => '', 'prefix_suffix' => TRUE],
      'value',
    ),
    'field_proposed_alt' => step8_view_config_field(
      'field_proposed_alt',
      'Proposed alt text',
      'basic_string',
      [],
      'value',
      max_length: 140,
    ),
    'field_source_framework' => step8_view_config_field(
      'field_source_framework',
      'Framework',
      'list_default',
      [],
      'value',
    ),
    'field_run_id' => step8_view_config_field(
      'field_run_id',
      'Run ID',
      'string',
      ['link_to_entity' => FALSE],
      'value',
      max_length: 30,
    ),
    'operations' => [
      'id' => 'operations',
      'table' => 'node',
      'field' => 'operations',
      'relationship' => 'none',
      'group_type' => 'group',
      'admin_label' => '',
      'plugin_id' => 'entity_operations',
      'label' => 'Actions',
      'exclude' => FALSE,
      'alter' => step8_view_alter_defaults(),
      'element_default_classes' => TRUE,
      'empty' => '',
      'hide_empty' => FALSE,
      'empty_zero' => FALSE,
      'hide_alter_empty' => TRUE,
      'destination' => TRUE,
    ],
  ];

  $filters = [
    'type' => [
      'id' => 'type',
      'table' => 'node_field_data',
      'field' => 'type',
      'relationship' => 'none',
      'group_type' => 'group',
      'admin_label' => '',
      'entity_type' => 'node',
      'entity_field' => 'type',
      'plugin_id' => 'bundle',
      'operator' => 'in',
      'value' => [STEP8_BUNDLE => STEP8_BUNDLE],
      'group' => 1,
      'exposed' => FALSE,
      'expose' => step8_view_expose_defaults(),
      'is_grouped' => FALSE,
      'group_info' => step8_view_group_info_defaults(),
    ],
    'field_review_status_value' => [
      'id' => 'field_review_status_value',
      'table' => 'node__field_review_status',
      'field' => 'field_review_status_value',
      'relationship' => 'none',
      'group_type' => 'group',
      'admin_label' => '',
      'plugin_id' => 'list_field',
      'operator' => 'in',
      'value' => ['pending' => 'pending'],
      'group' => 1,
      'exposed' => FALSE,
      'expose' => step8_view_expose_defaults(),
      'is_grouped' => FALSE,
      'group_info' => step8_view_group_info_defaults(),
    ],
    'field_source_framework_value' => [
      'id' => 'field_source_framework_value',
      'table' => 'node__field_source_framework',
      'field' => 'field_source_framework_value',
      'relationship' => 'none',
      'group_type' => 'group',
      'admin_label' => '',
      'plugin_id' => 'list_field',
      'operator' => 'in',
      'value' => [],
      'group' => 1,
      'exposed' => TRUE,
      'expose' => array_replace(step8_view_expose_defaults(), [
        'operator_id' => 'field_source_framework_value_op',
        'label' => 'Source framework',
        'operator' => 'field_source_framework_value_op',
        'identifier' => 'source_framework',
        'multiple' => FALSE,
        'reduce' => FALSE,
      ]),
      'is_grouped' => FALSE,
      'group_info' => step8_view_group_info_defaults(),
    ],
  ];

  $style_info = [];
  foreach (array_keys($fields) as $field_id) {
    $style_info[$field_id] = [
      'sortable' => in_array($field_id, ['title', 'field_target_node', 'field_source_framework'], TRUE),
      'default_sort_order' => 'asc',
      'align' => '',
      'separator' => '',
      'empty_column' => FALSE,
      'responsive' => in_array($field_id, ['field_target_revision', 'field_run_id'], TRUE)
        ? 'priority-low'
        : '',
    ];
  }

  $display = [
    'default' => [
      'id' => 'default',
      'display_title' => 'Default',
      'display_plugin' => 'default',
      'position' => 0,
      'display_options' => [
        'title' => 'Alt text review queue',
        'fields' => $fields,
        'pager' => [
          'type' => 'full',
          'options' => [
            'offset' => 0,
            'pagination_heading_level' => 'h4',
            'items_per_page' => 25,
            'total_pages' => 0,
            'id' => 0,
            'tags' => [
              'next' => 'Next ›',
              'previous' => '‹ Previous',
              'first' => '« First',
              'last' => 'Last »',
            ],
            'expose' => [
              'items_per_page' => FALSE,
              'items_per_page_label' => 'Items per page',
              'items_per_page_options' => '10, 25, 50',
              'items_per_page_options_all' => FALSE,
              'items_per_page_options_all_label' => '- All -',
              'offset' => FALSE,
              'offset_label' => 'Offset',
            ],
            'quantity' => 9,
          ],
        ],
        'exposed_form' => [
          'type' => 'basic',
          'options' => [
            'submit_button' => 'Filter',
            'reset_button' => TRUE,
            'reset_button_label' => 'Reset',
            'exposed_sorts_label' => 'Sort by',
            'expose_sort_order' => TRUE,
            'sort_asc_label' => 'Asc',
            'sort_desc_label' => 'Desc',
          ],
        ],
        'access' => [
          'type' => 'perm',
          'options' => ['perm' => 'access content overview'],
        ],
        'cache' => ['type' => 'tag'],
        'empty' => [
          'area_text_custom' => [
            'id' => 'area_text_custom',
            'table' => 'views',
            'field' => 'area_text_custom',
            'plugin_id' => 'text_custom',
            'empty' => TRUE,
            'content' => 'No pending alt text suggestions.',
          ],
        ],
        'sorts' => [
          'changed' => [
            'id' => 'changed',
            'table' => 'node_field_data',
            'field' => 'changed',
            'relationship' => 'none',
            'group_type' => 'group',
            'admin_label' => '',
            'entity_type' => 'node',
            'entity_field' => 'changed',
            'plugin_id' => 'date',
            'order' => 'DESC',
            'expose' => ['label' => ''],
            'exposed' => FALSE,
            'granularity' => 'second',
          ],
        ],
        'arguments' => [],
        'filters' => $filters,
        'filter_groups' => ['operator' => 'AND', 'groups' => [1 => 'AND']],
        'style' => [
          'type' => 'table',
          'options' => [
            'grouping' => [],
            'row_class' => '',
            'default_row_class' => TRUE,
            'columns' => array_combine(array_keys($fields), array_keys($fields)),
            'default' => '-1',
            'info' => $style_info,
            'override' => TRUE,
            'sticky' => TRUE,
            'summary' => 'Pending alt text recommendations awaiting human review.',
            'empty_table' => TRUE,
            'caption' => '',
            'description' => '',
            'class' => '',
          ],
        ],
        'row' => ['type' => 'fields'],
        'query' => [
          'type' => 'views_query',
          'options' => [
            'query_comment' => '',
            'disable_sql_rewrite' => FALSE,
            'distinct' => FALSE,
            'replica' => FALSE,
            'query_tags' => [],
          ],
        ],
        'relationships' => [],
        'header' => [],
        'footer' => [],
        'show_admin_links' => FALSE,
        'display_extenders' => [],
      ],
    ],
    'page_1' => [
      'id' => 'page_1',
      'display_title' => 'Review queue page',
      'display_plugin' => 'page',
      'position' => 1,
      'display_options' => [
        'path' => STEP8_VIEW_PATH,
        'menu' => [
          'type' => 'normal',
          'title' => 'Alt text review queue',
          'description' => 'Review AI-generated alt text recommendations.',
          'weight' => 20,
          'menu_name' => 'admin',
          'parent' => 'system.admin_content',
          'context' => '',
        ],
        'display_extenders' => [],
      ],
    ],
  ];

  $values = [
    'id' => STEP8_VIEW_ID,
    'label' => 'Alt text review queue',
    'status' => TRUE,
    'module' => 'node',
    'description' => 'Pending, revisioned alt-text recommendations awaiting human review.',
    'tag' => 'Agentic Harness Lab',
    'base_table' => 'node_field_data',
    'base_field' => 'nid',
    'display' => $display,
  ];

  $view = View::load(STEP8_VIEW_ID);
  if ($view === NULL) {
    $view = View::create($values);
    $view->save();
    step8_ok(sprintf('Created View at /%s.', STEP8_VIEW_PATH));
    return;
  }

  if ($view->get('base_table') !== 'node_field_data') {
    step8_fail(sprintf(
      'A View named %s already exists with an incompatible base table. Rename or remove it manually.',
      STEP8_VIEW_ID,
    ));
  }

  foreach ($values as $property => $value) {
    $view->set($property, $value);
  }
  $view->save();
  step8_note('Review queue View already existed; replaced it with the Step 8 definition.');
}

/**
 * Creates a base-table field handler configuration.
 *
 * @param array<string, mixed> $settings
 *
 * @return array<string, mixed>
 */
function step8_view_base_field(
  string $id,
  string $table,
  string $label,
  string $formatter,
  array $settings,
): array {
  return [
    'id' => $id,
    'table' => $table,
    'field' => $id,
    'relationship' => 'none',
    'group_type' => 'group',
    'admin_label' => '',
    'entity_type' => 'node',
    'entity_field' => $id,
    'plugin_id' => 'field',
    'label' => $label,
    'exclude' => FALSE,
    'alter' => step8_view_alter_defaults(),
    'element_default_classes' => TRUE,
    'empty' => '',
    'hide_empty' => FALSE,
    'empty_zero' => FALSE,
    'hide_alter_empty' => TRUE,
    'click_sort_column' => 'value',
    'type' => $formatter,
    'settings' => $settings,
    'group_column' => 'value',
    'group_columns' => [],
    'group_rows' => TRUE,
    'delta_limit' => 0,
    'delta_offset' => 0,
    'delta_reversed' => FALSE,
    'delta_first_last' => FALSE,
    'multi_type' => 'separator',
    'separator' => ', ',
    'field_api_classes' => FALSE,
  ];
}

/**
 * Creates a configurable-field View handler configuration.
 *
 * @param array<string, mixed> $settings
 *
 * @return array<string, mixed>
 */
function step8_view_config_field(
  string $field_name,
  string $label,
  string $formatter,
  array $settings,
  string $group_column,
  int $max_length = 0,
): array {
  $alter = step8_view_alter_defaults();
  if ($max_length > 0) {
    $alter['max_length'] = $max_length;
    $alter['trim'] = TRUE;
    $alter['word_boundary'] = TRUE;
    $alter['ellipsis'] = TRUE;
  }

  return [
    'id' => $field_name,
    'table' => 'node__' . $field_name,
    'field' => $field_name,
    'relationship' => 'none',
    'group_type' => 'group',
    'admin_label' => '',
    'plugin_id' => 'field',
    'label' => $label,
    'exclude' => FALSE,
    'alter' => $alter,
    'element_default_classes' => TRUE,
    'empty' => '',
    'hide_empty' => FALSE,
    'empty_zero' => FALSE,
    'hide_alter_empty' => TRUE,
    'click_sort_column' => $group_column,
    'type' => $formatter,
    'settings' => $settings,
    'group_column' => $group_column,
    'group_columns' => [],
    'group_rows' => TRUE,
    'delta_limit' => 0,
    'delta_offset' => 0,
    'delta_reversed' => FALSE,
    'delta_first_last' => FALSE,
    'multi_type' => 'separator',
    'separator' => ', ',
    'field_api_classes' => FALSE,
  ];
}

/**
 * @return array<string, mixed>
 */
function step8_view_alter_defaults(): array {
  return [
    'alter_text' => FALSE,
    'text' => '',
    'make_link' => FALSE,
    'path' => '',
    'absolute' => FALSE,
    'external' => FALSE,
    'replace_spaces' => FALSE,
    'path_case' => 'none',
    'trim_whitespace' => FALSE,
    'alt' => '',
    'rel' => '',
    'link_class' => '',
    'prefix' => '',
    'suffix' => '',
    'target' => '',
    'nl2br' => FALSE,
    'max_length' => 0,
    'word_boundary' => TRUE,
    'ellipsis' => TRUE,
    'more_link' => FALSE,
    'more_link_text' => '',
    'more_link_path' => '',
    'strip_tags' => FALSE,
    'trim' => FALSE,
    'preserve_tags' => '',
    'html' => FALSE,
  ];
}

/**
 * @return array<string, mixed>
 */
function step8_view_expose_defaults(): array {
  return [
    'operator_id' => '',
    'label' => '',
    'description' => '',
    'use_operator' => FALSE,
    'operator' => '',
    'operator_limit_selection' => FALSE,
    'operator_list' => [],
    'identifier' => '',
    'required' => FALSE,
    'remember' => FALSE,
    'multiple' => FALSE,
    'remember_roles' => ['authenticated' => 'authenticated'],
    'reduce' => FALSE,
  ];
}

/**
 * @return array<string, mixed>
 */
function step8_view_group_info_defaults(): array {
  return [
    'label' => '',
    'description' => '',
    'identifier' => '',
    'optional' => TRUE,
    'widget' => 'select',
    'multiple' => FALSE,
    'remember' => FALSE,
    'default_group' => 'All',
    'default_group_multiple' => [],
    'group_items' => [],
  ];
}

/**
 * Removes Step 8 entities after an explicit confirmation.
 */
function step8_remove(): void {
  $view = View::load(STEP8_VIEW_ID);
  if ($view !== NULL) {
    $view->delete();
    step8_ok('Deleted the alt text review queue View.');
  }

  $node_storage = \Drupal::entityTypeManager()->getStorage('node');
  $ids = $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP8_BUNDLE)
    ->execute();
  if ($ids !== []) {
    $nodes = $node_storage->loadMultiple($ids);
    $node_storage->delete($nodes);
    step8_warn(sprintf('Deleted %d alt_text_suggestion node(s).', count($nodes)));
  }

  foreach (['title', 'status'] as $base_field) {
    $override = BaseFieldOverride::loadByName('node', STEP8_BUNDLE, $base_field);
    if ($override !== NULL) {
      $override->delete();
    }
  }

  foreach (array_keys(step8_field_definitions()) as $field_name) {
    $field = FieldConfig::loadByName('node', STEP8_BUNDLE, $field_name);
    if ($field !== NULL) {
      $field->delete();
    }
  }

  /** @var \Drupal\node\NodeTypeInterface|null $type */
  $type = \Drupal::entityTypeManager()->getStorage('node_type')->load(STEP8_BUNDLE);
  if ($type !== NULL) {
    $type->delete();
    step8_ok('Deleted the alt_text_suggestion content type.');
  }

  $field_config_storage = \Drupal::entityTypeManager()->getStorage('field_config');
  foreach (array_keys(step8_field_definitions()) as $field_name) {
    $remaining = $field_config_storage->loadByProperties([
      'entity_type' => 'node',
      'field_name' => $field_name,
    ]);
    if ($remaining !== []) {
      step8_warn(sprintf('Kept node.%s storage because another bundle still uses it.', $field_name));
      continue;
    }

    $storage = FieldStorageConfig::loadByName('node', $field_name);
    if ($storage !== NULL) {
      $storage->delete();
      step8_ok(sprintf('Deleted unused field storage: node.%s', $field_name));
    }
  }

  step8_ok('Phase 0 Step 8 removal completed. Roles and accounts were not changed.');
}

/**
 * Audits the content type, fields, displays, and review queue.
 */
function step8_audit(): void {
  step8_line('');
  step8_line('=== Phase 0 Step 8 audit ===');
  $unsafe = FALSE;

  // Prerequisite Article structure used by the Step 9 deterministic dataset.
  /** @var \Drupal\node\NodeTypeInterface|null $article */
  $article = \Drupal::entityTypeManager()->getStorage('node_type')->load('article');
  if ($article === NULL) {
    step8_error('Missing prerequisite content type: article');
    $unsafe = TRUE;
  }
  else {
    step8_ok('Prerequisite content type exists: Article.');
  }

  $article_body = FieldConfig::loadByName('node', 'article', 'body');
  if ($article_body === NULL) {
    step8_error('Article is missing the Body field.');
    $unsafe = TRUE;
  }
  else {
    step8_ok('Article Body field is attached.');
  }

  $article_image_storage = FieldStorageConfig::loadByName('node', 'field_image');
  $article_image = FieldConfig::loadByName('node', 'article', 'field_image');
  if ($article_image_storage === NULL || $article_image === NULL) {
    step8_error('Article is missing field_image or its storage.');
    $unsafe = TRUE;
  }
  else {
    $image_cardinality = $article_image_storage->getCardinality();
    $alt_required = (bool) $article_image->getSetting('alt_field_required');
    if ($article_image_storage->getType() !== 'image') {
      step8_error('node.field_image is not an image field.');
      $unsafe = TRUE;
    }
    elseif ($image_cardinality !== -1 && $image_cardinality < 2) {
      step8_error(sprintf('node.field_image cardinality is %d; expected at least 2.', $image_cardinality));
      $unsafe = TRUE;
    }
    elseif ($alt_required) {
      step8_error('Article image alt text is required; Step 9 needs controlled missing-alt fixtures.');
      $unsafe = TRUE;
    }
    else {
      step8_ok(sprintf(
        'Article field_image is ready; cardinality=%s; alt required=no.',
        $image_cardinality === -1 ? 'unlimited' : (string) $image_cardinality,
      ));
    }
  }

  /** @var \Drupal\node\NodeTypeInterface|null $type */
  $type = \Drupal::entityTypeManager()->getStorage('node_type')->load(STEP8_BUNDLE);
  if ($type === NULL) {
    step8_error('Missing content type: alt_text_suggestion');
    $unsafe = TRUE;
  }
  else {
    $new_revision = (bool) $type->get('new_revision');
    step8_line(sprintf(
      'Content type: %s; revisions by default=%s',
      $type->label(),
      $new_revision ? 'yes' : 'no',
    ));
    if (!$new_revision) {
      step8_error('alt_text_suggestion is not configured to create a new revision on each save.');
      $unsafe = TRUE;
    }
  }

  $status_override = BaseFieldOverride::loadByName('node', STEP8_BUNDLE, 'status');
  $status_default = $status_override?->getDefaultValueLiteral() ?? [];
  if (($status_default[0]['value'] ?? NULL) !== 1) {
    step8_error('Suggestion nodes are not published by default; editor_dana may not see agent-created records with the Step 7 permission model.');
    $unsafe = TRUE;
  }
  else {
    step8_ok('Suggestion nodes default to published for this dummy-data lab.');
  }

  foreach (step8_field_definitions() as $field_name => $definition) {
    $storage = FieldStorageConfig::loadByName('node', $field_name);
    $field = FieldConfig::loadByName('node', STEP8_BUNDLE, $field_name);

    if ($storage === NULL || $field === NULL) {
      step8_error(sprintf('Missing field storage or bundle field: %s', $field_name));
      $unsafe = TRUE;
      continue;
    }

    $issues = [];
    if ($storage->getType() !== $definition['type']) {
      $issues[] = sprintf('type=%s expected=%s', $storage->getType(), $definition['type']);
    }
    if ($storage->getCardinality() !== 1) {
      $issues[] = sprintf('cardinality=%d expected=1', $storage->getCardinality());
    }
    foreach ($definition['storage_settings'] as $key => $expected) {
      if ($storage->getSetting($key) !== $expected) {
        $issues[] = sprintf('storage setting %s differs', $key);
      }
    }
    if ($field->isRequired() !== $definition['required']) {
      $issues[] = sprintf('required=%s expected=%s',
        $field->isRequired() ? 'true' : 'false',
        $definition['required'] ? 'true' : 'false',
      );
    }

    if ($issues === []) {
      step8_ok(sprintf('%s: %s; required=%s',
        $field_name,
        $storage->getType(),
        $field->isRequired() ? 'yes' : 'no',
      ));
    }
    else {
      step8_error(sprintf('%s: %s', $field_name, implode('; ', $issues)));
      $unsafe = TRUE;
    }
  }

  $form_display = \Drupal::entityTypeManager()
    ->getStorage('entity_form_display')
    ->load('node.' . STEP8_BUNDLE . '.default');
  if ($form_display === NULL) {
    step8_error('Missing default reviewer form display.');
    $unsafe = TRUE;
  }
  else {
    foreach (array_keys(step8_field_definitions()) as $field_name) {
      if ($form_display->getComponent($field_name) === NULL) {
        step8_error(sprintf('Reviewer form is missing component: %s', $field_name));
        $unsafe = TRUE;
      }
    }
    step8_ok('Reviewer form display contains all Step 8 fields.');
  }

  $view = View::load(STEP8_VIEW_ID);
  if ($view === NULL) {
    step8_error('Missing View: alt_text_review_queue');
    $unsafe = TRUE;
  }
  else {
    $display = $view->get('display');
    $default_options = $display['default']['display_options'] ?? [];
    $page_options = $display['page_1']['display_options'] ?? [];

    $path = $page_options['path'] ?? NULL;
    $access_permission = $default_options['access']['options']['perm'] ?? NULL;
    $bundle_filter = $default_options['filters']['type']['value'][STEP8_BUNDLE] ?? NULL;
    $status_filter = $default_options['filters']['field_review_status_value']['value']['pending'] ?? NULL;
    $source_filter = $default_options['filters']['field_source_framework_value'] ?? [];
    $style = $default_options['style']['type'] ?? NULL;

    step8_line(sprintf('Review queue path: /%s', (string) $path));
    step8_line(sprintf('Review queue access permission: %s', (string) $access_permission));

    $checks = [
      'path' => $path === STEP8_VIEW_PATH,
      'permission access' => $access_permission === 'access content overview',
      'bundle filter' => $bundle_filter === STEP8_BUNDLE,
      'pending default filter' => $status_filter === 'pending',
      'source framework exposed filter' => ($source_filter['exposed'] ?? FALSE) === TRUE
        && ($source_filter['expose']['identifier'] ?? NULL) === 'source_framework',
      'table style' => $style === 'table',
    ];

    foreach ($checks as $label => $passed) {
      if ($passed) {
        step8_ok('View check: ' . $label);
      }
      else {
        step8_error('View check failed: ' . $label);
        $unsafe = TRUE;
      }
    }
  }

  if ($unsafe) {
    step8_fail('Audit found one or more incomplete or incompatible Step 8 conditions.');
  }

  step8_ok('Audit passed.');
}

function step8_line(string $message): void {
  fwrite(STDOUT, $message . PHP_EOL);
}

function step8_ok(string $message): void {
  step8_line('[OK] ' . $message);
}

function step8_note(string $message): void {
  step8_line('[INFO] ' . $message);
}

function step8_warn(string $message): void {
  step8_line('[WARN] ' . $message);
}

function step8_error(string $message): void {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
}

function step8_fail(string $message): never {
  step8_error($message);
  exit(1);
}
