<?php

declare(strict_types=1);

/**
 * Emits the active Gate 0.5 queue configuration without UUIDs or secrets.
 *
 * Usage:
 *   ddev drush --quiet php:script scripts/gate05-step05-config.php -- snapshot
 */

use Drupal\Core\Entity\Display\EntityFormDisplayInterface;
use Drupal\Core\Entity\Display\EntityViewDisplayInterface;
use Drupal\field\Entity\FieldConfig;
use Drupal\field\Entity\FieldStorageConfig;
use Drupal\node\NodeTypeInterface;
use Drupal\user\RoleInterface;
use Drupal\views\ViewEntityInterface;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';

if ($mode !== 'snapshot') {
  fwrite(STDERR, "[ERROR] Use: snapshot\n");
  exit(1);
}

$field_expectations = [
  'field_target_node' => 'entity_reference',
  'field_target_revision' => 'integer',
  'field_target_field' => 'string',
  'field_target_delta' => 'integer',
  'field_target_file' => 'entity_reference',
  'field_proposed_alt' => 'string_long',
  'field_review_status' => 'list_string',
  'field_source_framework' => 'list_string',
  'field_run_id' => 'string',
  'field_evidence_hash' => 'string',
];

$entity_type_manager = \Drupal::entityTypeManager();

$node_type = $entity_type_manager
  ->getStorage('node_type')
  ->load('alt_text_suggestion');
if (!$node_type instanceof NodeTypeInterface) {
  gate05_step05_config_fail('Missing alt_text_suggestion content type.');
}

$fields = [];
foreach ($field_expectations as $field_name => $expected_type) {
  $storage = FieldStorageConfig::loadByName('node', $field_name);
  $field = FieldConfig::loadByName(
    'node',
    'alt_text_suggestion',
    $field_name,
  );

  if (!$storage instanceof FieldStorageConfig) {
    gate05_step05_config_fail('Missing field storage: ' . $field_name);
  }
  if (!$field instanceof FieldConfig) {
    gate05_step05_config_fail('Missing queue field: ' . $field_name);
  }
  if ($storage->getType() !== $expected_type) {
    gate05_step05_config_fail(
      sprintf(
        'Unexpected type for %s: %s',
        $field_name,
        $storage->getType(),
      ),
    );
  }

  $storage_settings = $storage->getSettings();
  $field_settings = $field->getSettings();

  $semantic_storage = [];
  foreach ([
    'target_type',
    'max_length',
    'case_sensitive',
    'is_ascii',
    'unsigned',
    'size',
    'allowed_values',
  ] as $setting_name) {
    if (array_key_exists($setting_name, $storage_settings)) {
      $semantic_storage[$setting_name] = $storage_settings[$setting_name];
    }
  }

  $semantic_field = [];
  foreach (['handler', 'handler_settings', 'min', 'max'] as $setting_name) {
    if (array_key_exists($setting_name, $field_settings)) {
      $semantic_field[$setting_name] = $field_settings[$setting_name];
    }
  }

  $fields[$field_name] = [
    'type' => $storage->getType(),
    'cardinality' => $storage->getCardinality(),
    'required' => $field->isRequired(),
    'storage_settings' => $semantic_storage,
    'field_settings' => $semantic_field,
  ];
}
ksort($fields);

$form_display = $entity_type_manager
  ->getStorage('entity_form_display')
  ->load('node.alt_text_suggestion.default');
if (!$form_display instanceof EntityFormDisplayInterface) {
  gate05_step05_config_fail('Missing default recommendation form display.');
}

$view_display = $entity_type_manager
  ->getStorage('entity_view_display')
  ->load('node.alt_text_suggestion.default');
if (!$view_display instanceof EntityViewDisplayInterface) {
  gate05_step05_config_fail('Missing default recommendation view display.');
}

$form_widgets = [];
$view_formatters = [];
foreach (array_keys($field_expectations) as $field_name) {
  $form_component = $form_display->getComponent($field_name);
  $view_component = $view_display->getComponent($field_name);
  if (!is_array($form_component) || !isset($form_component['type'])) {
    gate05_step05_config_fail(
      'Missing form widget for queue field: ' . $field_name,
    );
  }
  if (!is_array($view_component) || !isset($view_component['type'])) {
    gate05_step05_config_fail(
      'Missing view formatter for queue field: ' . $field_name,
    );
  }
  $form_widgets[$field_name] = (string) $form_component['type'];
  $view_formatters[$field_name] = (string) $view_component['type'];
}
ksort($form_widgets);
ksort($view_formatters);

$agent_role = $entity_type_manager
  ->getStorage('user_role')
  ->load('agent_service');
$editor_role = $entity_type_manager
  ->getStorage('user_role')
  ->load('content_editor');
if (!$agent_role instanceof RoleInterface) {
  gate05_step05_config_fail('Missing agent_service role.');
}
if (!$editor_role instanceof RoleInterface) {
  gate05_step05_config_fail('Missing content_editor role.');
}

$agent_permissions = array_values($agent_role->getPermissions());
$editor_permissions = array_values($editor_role->getPermissions());
sort($agent_permissions);
sort($editor_permissions);

$review_view = $entity_type_manager
  ->getStorage('view')
  ->load('alt_text_review_queue');
if (!$review_view instanceof ViewEntityInterface) {
  gate05_step05_config_fail('Missing alt_text_review_queue view.');
}

$review_path = NULL;
$display_config = $review_view->get('display');
if (is_array($display_config)) {
  foreach ($display_config as $display) {
    if (
      is_array($display)
      && ($display['display_plugin'] ?? NULL) === 'page'
      && isset($display['display_options']['path'])
    ) {
      $review_path = (string) $display['display_options']['path'];
      break;
    }
  }
}
if ($review_path === NULL || $review_path === '') {
  gate05_step05_config_fail('Review queue page path is missing.');
}

$result = [
  'schema_version' => 1,
  'status' => 'pass',
  'content_type' => [
    'bundle' => 'alt_text_suggestion',
    'new_revision' => $node_type->shouldCreateNewRevision(),
  ],
  'fields' => $fields,
  'form_widgets' => $form_widgets,
  'view_formatters' => $view_formatters,
  'roles' => [
    'agent_service' => $agent_permissions,
    'content_editor' => $editor_permissions,
  ],
  'review_queue' => [
    'view_id' => 'alt_text_review_queue',
    'path' => $review_path,
  ],
];

print json_encode(
  gate05_step05_config_sort($result),
  JSON_PRETTY_PRINT
    | JSON_UNESCAPED_SLASHES
    | JSON_UNESCAPED_UNICODE
    | JSON_THROW_ON_ERROR,
) . PHP_EOL;

function gate05_step05_config_fail(string $message): never {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
  exit(1);
}

function gate05_step05_config_sort(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate05_step05_config_sort', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate05_step05_config_sort($item);
  }
  return $value;
}
