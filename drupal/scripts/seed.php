<?php

declare(strict_types=1);

/**
 * Phase 0, Step 9: deterministic Drupal seed dataset.
 *
 * Run from the Drupal project root:
 *
 *   ddev drush php:script scripts/seed.php
 *   ddev drush php:script scripts/seed.php -- apply
 *   ddev drush php:script scripts/seed.php -- audit
 *   ddev drush php:script scripts/seed.php -- manifest
 *   ddev drush php:script scripts/seed.php -- remove confirm
 *
 * The script creates only synthetic lab content. It is idempotent: rerunning
 * apply reuses deterministic UUIDs and does not create a new node revision when
 * the current record already matches the expected fixture.
 */

use Drupal\Core\File\FileExists;
use Drupal\file\Entity\File;
use Drupal\node\Entity\Node;
use Drupal\node\NodeInterface;

const STEP9_SCRIPT_VERSION = '1.0.0';
const STEP9_ARTICLE_BUNDLE = 'article';
const STEP9_SUGGESTION_BUNDLE = 'alt_text_suggestion';
const STEP9_IMAGE_FIELD = 'field_image';
const STEP9_FILE_DIRECTORY = 'public://phase0-step9-seed';
const STEP9_NAMESPACE_UUID = '24f0d9ba-f4c6-5a70-a2f1-d88f8c9bf510';
const STEP9_IMAGE_WIDTH = 1200;
const STEP9_IMAGE_HEIGHT = 675;
const STEP9_EXPECTED_ARTICLES = 20;
const STEP9_EXPECTED_FILES = 30;
const STEP9_EXPECTED_TARGETS = 12;
const STEP9_EXPECTED_MISSING = 9;
const STEP9_EXPECTED_POOR = 3;

$script_args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $script_args[0] ?? 'apply';
$confirmation = $script_args[1] ?? '';

if (!in_array($mode, ['apply', 'audit', 'manifest', 'remove'], TRUE)) {
  step9_fail(sprintf(
    'Unknown mode "%s". Use one of: apply, audit, manifest, remove.',
    $mode,
  ));
}

if ($mode === 'remove' && $confirmation !== 'confirm') {
  step9_fail('Removal is destructive. Run again as: remove confirm');
}

step9_require_environment();

if ($mode !== 'manifest') {
  step9_note('Step 9 script version: ' . STEP9_SCRIPT_VERSION);
}

if ($mode === 'audit') {
  step9_audit(TRUE);
  return;
}

if ($mode === 'manifest') {
  step9_print_manifest();
  return;
}

if ($mode === 'remove') {
  step9_remove();
  return;
}

step9_apply();
step9_audit(TRUE);
step9_ok('Phase 0 Step 9 apply mode completed.');
step9_note('Next: inspect a few seeded Articles, then create the seeded-clean snapshot in Step 10.');

/**
 * Returns the deterministic 20-Article fixture definition.
 *
 * Odd-numbered Articles contain one image. Even-numbered Articles contain two.
 * The first 12 Articles each contain exactly one target usage; Articles 13-20
 * are fully covered. Target deltas intentionally vary between 0 and 1.
 *
 * @return array<int, array<string, mixed>>
 */
function step9_dataset(): array {
  $records = [
    1 => ['Emergency Preparedness Checklist', 'emergency preparedness', 'explains how residents can assemble supplies, identify evacuation routes, and prepare household contact plans'],
    2 => ['Community Grant Application Guide', 'community grants', 'summarizes a fictional application process for neighborhood improvement grants'],
    3 => ['Public Meeting Accessibility Notice', 'accessible public meetings', 'describes demonstration accommodations and accessible participation options for a public meeting'],
    4 => ['Water Quality Monitoring Update', 'water quality monitoring', 'presents synthetic sampling information for a fictional community water program'],
    5 => ['Small Business Export Assistance', 'export assistance', 'outlines a fictional orientation program for small businesses exploring international markets'],
    6 => ['Seasonal Road Maintenance Schedule', 'road maintenance', 'describes a fictional seasonal schedule for inspection, repair, and snow-response preparation'],
    7 => ['Digital Records Retention Policy', 'records retention', 'summarizes a fictional records lifecycle and document-retention policy'],
    8 => ['Public Library Technology Program', 'library technology', 'announces fictional digital-skills workshops and device-support sessions'],
    9 => ['Workforce Training Enrollment', 'workforce training', 'describes a fictional enrollment process for job-readiness and technical training'],
    10 => ['Municipal Recycling Instructions', 'recycling instructions', 'explains a fictional sorting and collection process for household recycling'],
    11 => ['Broadband Availability Survey', 'broadband access', 'invites fictional residents to report internet availability and service-quality information'],
    12 => ['Park Facility Improvement Plan', 'park improvements', 'summarizes a fictional plan for trail, playground, and recreation-facility improvements'],
    13 => ['Veterans Services Office Hours', 'veterans services', 'lists fictional office hours and appointment options for a demonstration assistance program'],
    14 => ['Consumer Product Safety Bulletin', 'consumer safety', 'shares fictional reminders about reporting unsafe products and reviewing recall notices'],
    15 => ['Local Transit Rider Information', 'public transit', 'describes fictional route-planning, fare, and accessibility information for riders'],
    16 => ['Floodplain Mapping Update', 'floodplain mapping', 'explains a fictional map-review and public-comment process'],
    17 => ['Public Health Clinic Directory', 'public health clinics', 'provides fictional clinic-service categories and appointment guidance'],
    18 => ['Historic Preservation Grant Notice', 'historic preservation', 'announces a fictional preservation-grant cycle and eligibility overview'],
    19 => ['Open Data Portal Release Notes', 'open government data', 'summarizes fictional dataset additions and metadata improvements'],
    20 => ['Citizen Advisory Board Calendar', 'public advisory boards', 'lists fictional meeting dates and participation guidance for advisory boards'],
  ];

  $palette = [
    ['Navy', 31, 58, 99],
    ['Teal', 17, 94, 103],
    ['Maroon', 112, 42, 62],
    ['Olive', 92, 102, 45],
    ['Purple', 82, 55, 112],
    ['Blue', 35, 88, 144],
    ['Rust', 145, 68, 38],
    ['Green', 40, 108, 76],
    ['Slate', 68, 80, 94],
    ['Indigo', 63, 65, 132],
  ];

  $target_matrix = [
    1 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    2 => ['delta' => 1, 'state' => 'missing', 'alt' => ''],
    3 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    4 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    5 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    6 => ['delta' => 1, 'state' => 'missing', 'alt' => ''],
    7 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    8 => ['delta' => 1, 'state' => 'missing', 'alt' => ''],
    9 => ['delta' => 0, 'state' => 'missing', 'alt' => ''],
    10 => ['delta' => 1, 'state' => 'poor', 'alt' => 'image.jpg'],
    11 => ['delta' => 0, 'state' => 'poor', 'alt' => 'photo'],
    12 => ['delta' => 1, 'state' => 'poor', 'alt' => 'phase0-article-12-image-2.png'],
  ];

  $dataset = [];
  foreach ($records as $number => [$title, $topic, $description]) {
    [$color_name, $red, $green, $blue] = $palette[($number - 1) % count($palette)];
    $image_count = $number % 2 === 0 ? 2 : 1;
    $images = [];

    for ($slot = 1; $slot <= $image_count; $slot++) {
      $delta = $slot - 1;
      $filename = sprintf('phase0-article-%02d-image-%d.png', $number, $slot);
      $alt = sprintf(
        '%s demonstration placard labeled Article %d for %s%s',
        $color_name,
        $number,
        $topic,
        $slot === 2 ? ' supporting context' : '',
      );
      $state = 'acceptable';

      if (isset($target_matrix[$number]) && $target_matrix[$number]['delta'] === $delta) {
        $state = $target_matrix[$number]['state'];
        $alt = $target_matrix[$number]['alt'];
      }

      $images[] = [
        'delta' => $delta,
        'slot' => $slot,
        'filename' => $filename,
        'uri' => STEP9_FILE_DIRECTORY . '/' . $filename,
        'uuid' => step9_uuid_v5(STEP9_NAMESPACE_UUID, sprintf('file:%02d:%d', $number, $slot)),
        'alt' => $alt,
        'state' => $state,
        'color_name' => $color_name,
        'rgb' => [$red, $green, $blue],
      ];
    }

    $body = sprintf(
      "This is fictional demonstration content for the Drupal GovCon 2026 agentic-harness lab. It contains no real agency, program, resident, client, or operational data.\n\nThis article %s. Its generated illustration uses a solid %s background, a large visible Article %d identifier, a short topic label, and a primary or supporting-image label. The page and image are intentionally simple so context assembly, target provenance, validation, review, and recovery can be compared reproducibly across frameworks.",
      $description,
      strtolower($color_name),
      $number,
    );

    $dataset[$number] = [
      'number' => $number,
      'title' => sprintf('Phase 0 %02d — %s', $number, $title),
      'topic' => $topic,
      'description' => $description,
      'body' => $body,
      'uuid' => step9_uuid_v5(STEP9_NAMESPACE_UUID, sprintf('article:%02d', $number)),
      'images' => $images,
    ];
  }

  return $dataset;
}

/**
 * Creates or normalizes the deterministic fixture.
 */
function step9_apply(): void {
  $owner = step9_load_required_user('editor_dana');
  $format_id = step9_default_text_format();
  $file_system = \Drupal::service('file_system');
  $seed_directory = STEP9_FILE_DIRECTORY;
  $directory_ready = $file_system->prepareDirectory(
    $seed_directory,
    \Drupal\Core\File\FileSystemInterface::CREATE_DIRECTORY | \Drupal\Core\File\FileSystemInterface::MODIFY_PERMISSIONS,
  );
  if (!$directory_ready) {
    step9_fail('Could not create or write to ' . STEP9_FILE_DIRECTORY . '.');
  }

  $created_files = 0;
  $updated_files = 0;
  $unchanged_files = 0;
  $created_nodes = 0;
  $updated_nodes = 0;
  $unchanged_nodes = 0;

  foreach (step9_dataset() as $definition) {
    $image_values = [];

    foreach ($definition['images'] as $image_definition) {
      $result = step9_ensure_file($definition, $image_definition, (int) $owner->id());
      /** @var \Drupal\file\FileInterface $file */
      $file = $result['file'];
      match ($result['action']) {
        'created' => $created_files++,
        'updated' => $updated_files++,
        default => $unchanged_files++,
      };

      $image_values[] = [
        'target_id' => (int) $file->id(),
        'alt' => (string) $image_definition['alt'],
        'title' => '',
      ];
    }

    $result = step9_ensure_node($definition, $image_values, (int) $owner->id(), $format_id);
    match ($result) {
      'created' => $created_nodes++,
      'updated' => $updated_nodes++,
      default => $unchanged_nodes++,
    };
  }

  step9_ok(sprintf(
    'Files: %d created, %d updated, %d unchanged.',
    $created_files,
    $updated_files,
    $unchanged_files,
  ));
  step9_ok(sprintf(
    'Articles: %d created, %d updated, %d unchanged.',
    $created_nodes,
    $updated_nodes,
    $unchanged_nodes,
  ));
}

/**
 * Creates or updates one generated PNG and its permanent File entity.
 *
 * @param array<string, mixed> $article_definition
 * @param array<string, mixed> $image_definition
 *
 * @return array{file: \Drupal\file\FileInterface, action: string}
 */
function step9_ensure_file(array $article_definition, array $image_definition, int $owner_id): array {
  $png_data = step9_generate_png($article_definition, $image_definition);
  $uri = (string) $image_definition['uri'];
  $expected_uuid = (string) $image_definition['uuid'];
  $file_system = \Drupal::service('file_system');
  $real_path = $file_system->realpath($uri);
  $physical_matches = is_string($real_path)
    && is_file($real_path)
    && hash_file('sha256', $real_path) === hash('sha256', $png_data);

  $file = step9_load_entity_by_uuid('file', $expected_uuid);
  if ($file !== NULL && $file->getFileUri() !== $uri) {
    step9_fail(sprintf(
      'Deterministic file UUID %s already belongs to %s instead of %s.',
      $expected_uuid,
      $file->getFileUri(),
      $uri,
    ));
  }

  $uri_file = step9_load_file_by_uri($uri);
  if ($uri_file !== NULL && $file !== NULL && $uri_file->id() !== $file->id()) {
    step9_fail(sprintf(
      'File URI %s and deterministic UUID %s resolve to different File entities.',
      $uri,
      $expected_uuid,
    ));
  }
  if ($uri_file !== NULL && $file === NULL && $uri_file->uuid() !== $expected_uuid) {
    step9_fail(sprintf(
      'Seed URI %s is already owned by an unrelated File entity with UUID %s. No file was replaced.',
      $uri,
      $uri_file->uuid(),
    ));
  }

  $file ??= $uri_file;
  $action = 'unchanged';

  if (!$physical_matches) {
    $saved_uri = $file_system->saveData($png_data, $uri, FileExists::Replace);
    if ($saved_uri !== $uri) {
      step9_fail(sprintf('Expected generated image URI %s; received %s.', $uri, $saved_uri));
    }
    $action = $file === NULL ? 'created' : 'updated';
  }

  if ($file === NULL) {
    $file = File::create([
      'uuid' => $expected_uuid,
      'uri' => $uri,
      'uid' => $owner_id,
      'filename' => (string) $image_definition['filename'],
      'filemime' => 'image/png',
      'filesize' => strlen($png_data),
      'status' => 1,
    ]);
    $file->setPermanent();
    $file->save();
    $action = 'created';
  }
  else {
    $metadata_changed = FALSE;
    if (!$file->isPermanent()) {
      $file->setPermanent();
      $metadata_changed = TRUE;
    }
    if ((int) $file->getOwnerId() !== $owner_id) {
      $file->setOwnerId($owner_id);
      $metadata_changed = TRUE;
    }
    if ($file->getFilename() !== $image_definition['filename']) {
      $file->setFilename((string) $image_definition['filename']);
      $metadata_changed = TRUE;
    }
    if ($file->getMimeType() !== 'image/png') {
      $file->setMimeType('image/png');
      $metadata_changed = TRUE;
    }
    if ((int) $file->getSize() !== strlen($png_data)) {
      $file->setSize(strlen($png_data));
      $metadata_changed = TRUE;
    }
    if ($metadata_changed) {
      $file->save();
      if ($action === 'unchanged') {
        $action = 'updated';
      }
    }
  }

  return ['file' => $file, 'action' => $action];
}

/**
 * Creates or normalizes one Article without making no-op revisions.
 *
 * @param array<string, mixed> $definition
 * @param array<int, array<string, mixed>> $image_values
 */
function step9_ensure_node(array $definition, array $image_values, int $owner_id, string $format_id): string {
  /** @var \Drupal\node\NodeInterface|null $node */
  $node = step9_load_entity_by_uuid('node', (string) $definition['uuid']);
  if ($node !== NULL && $node->bundle() !== STEP9_ARTICLE_BUNDLE) {
    step9_fail(sprintf(
      'Deterministic node UUID %s belongs to bundle %s, not Article.',
      $definition['uuid'],
      $node->bundle(),
    ));
  }

  $title_matches = step9_load_nodes_by_title((string) $definition['title']);
  foreach ($title_matches as $title_match) {
    if ($title_match->uuid() !== $definition['uuid']) {
      step9_fail(sprintf(
        'Seed title "%s" already belongs to node %d with unrelated UUID %s. No duplicate was created.',
        $definition['title'],
        $title_match->id(),
        $title_match->uuid(),
      ));
    }
  }

  $values = [
    'title' => (string) $definition['title'],
    'uid' => $owner_id,
    'status' => 1,
    'promote' => 0,
    'sticky' => 0,
    'body' => [[
      'value' => (string) $definition['body'],
      'format' => $format_id,
    ]],
    STEP9_IMAGE_FIELD => $image_values,
  ];

  if ($node === NULL) {
    $created = 1782864000 + ((int) $definition['number'] * 60);
    $node = Node::create($values + [
      'type' => STEP9_ARTICLE_BUNDLE,
      'uuid' => (string) $definition['uuid'],
      'created' => $created,
      'changed' => $created,
    ]);
    $node->setNewRevision(TRUE);
    $node->setRevisionUserId($owner_id);
    $node->setRevisionLogMessage('Created by Phase 0 Step 9 deterministic seed v' . STEP9_SCRIPT_VERSION . '.');
    $node->save();
    return 'created';
  }

  if (step9_node_matches($node, $values)) {
    return 'unchanged';
  }

  foreach ($values as $field_name => $value) {
    $node->set($field_name, $value);
  }
  $node->setNewRevision(TRUE);
  $node->setRevisionUserId($owner_id);
  $node->setRevisionLogMessage('Normalized by Phase 0 Step 9 deterministic seed v' . STEP9_SCRIPT_VERSION . '.');
  $node->save();
  return 'updated';
}

/**
 * Checks whether an existing node already matches the exact seed definition.
 *
 * @param array<string, mixed> $expected
 */
function step9_node_matches(NodeInterface $node, array $expected): bool {
  if ($node->label() !== $expected['title']) {
    return FALSE;
  }
  if ((int) $node->getOwnerId() !== (int) $expected['uid']) {
    return FALSE;
  }
  if ((int) $node->isPublished() !== (int) $expected['status']) {
    return FALSE;
  }
  if ((int) $node->isPromoted() !== (int) $expected['promote']) {
    return FALSE;
  }
  if ((int) $node->isSticky() !== (int) $expected['sticky']) {
    return FALSE;
  }

  $body = $node->get('body')->first();
  $expected_body = $expected['body'][0];
  if ($body === NULL
    || (string) $body->value !== (string) $expected_body['value']
    || (string) $body->format !== (string) $expected_body['format']) {
    return FALSE;
  }

  $current_images = [];
  foreach ($node->get(STEP9_IMAGE_FIELD) as $item) {
    $current_images[] = [
      'target_id' => (int) $item->target_id,
      'alt' => (string) $item->alt,
      'title' => (string) $item->title,
    ];
  }

  $expected_images = array_map(
    static fn(array $item): array => [
      'target_id' => (int) $item['target_id'],
      'alt' => (string) $item['alt'],
      'title' => (string) ($item['title'] ?? ''),
    ],
    $expected[STEP9_IMAGE_FIELD],
  );

  return $current_images === $expected_images;
}

/**
 * Audits the seed and optionally prints a readable report.
 *
 * @return array<int, array<string, mixed>>
 *   The current 12-target manifest.
 */
function step9_audit(bool $verbose): array {
  $errors = [];
  $manifest = [];
  $dataset = step9_dataset();
  $seed_node_ids = [];
  $seed_file_ids = [];
  $article_count = 0;
  $file_count = 0;
  $missing_count = 0;
  $poor_count = 0;
  $acceptable_node_count = 0;

  foreach ($dataset as $definition) {
    /** @var \Drupal\node\NodeInterface|null $node */
    $node = step9_load_entity_by_uuid('node', (string) $definition['uuid']);
    if ($node === NULL) {
      $errors[] = sprintf('Missing Article %02d (%s).', $definition['number'], $definition['uuid']);
      continue;
    }
    $article_count++;
    $seed_node_ids[] = (int) $node->id();

    $title_matches = step9_load_nodes_by_title((string) $definition['title']);
    if (count($title_matches) !== 1 || reset($title_matches)->uuid() !== $definition['uuid']) {
      $errors[] = sprintf(
        'Seed title "%s" does not resolve uniquely to its deterministic UUID.',
        $definition['title'],
      );
    }

    if ($node->bundle() !== STEP9_ARTICLE_BUNDLE) {
      $errors[] = sprintf('Seed node %s has bundle %s.', $node->uuid(), $node->bundle());
      continue;
    }
    if ($node->label() !== $definition['title']) {
      $errors[] = sprintf('Article %02d title drifted: %s', $definition['number'], $node->label());
    }
    if (!$node->isPublished()) {
      $errors[] = sprintf('Article %02d is not published.', $definition['number']);
    }
    if (!$node->hasField(STEP9_IMAGE_FIELD)) {
      $errors[] = sprintf('Article %02d has no %s field.', $definition['number'], STEP9_IMAGE_FIELD);
      continue;
    }

    $items = $node->get(STEP9_IMAGE_FIELD);
    if ($items->count() !== count($definition['images'])) {
      $errors[] = sprintf(
        'Article %02d has %d images; expected %d.',
        $definition['number'],
        $items->count(),
        count($definition['images']),
      );
    }

    $node_has_target = FALSE;
    foreach ($definition['images'] as $image_definition) {
      $delta = (int) $image_definition['delta'];
      $item = $items->get($delta);
      if ($item === NULL || $item->isEmpty()) {
        $errors[] = sprintf('Article %02d image delta %d is missing.', $definition['number'], $delta);
        continue;
      }

      /** @var \Drupal\file\FileInterface|null $file */
      $file = $item->entity;
      if ($file === NULL) {
        $errors[] = sprintf('Article %02d delta %d references no File entity.', $definition['number'], $delta);
        continue;
      }
      $seed_file_ids[] = (int) $file->id();
      $file_count++;

      if ($file->uuid() !== $image_definition['uuid']) {
        $errors[] = sprintf(
          'Article %02d delta %d file UUID is %s; expected %s.',
          $definition['number'],
          $delta,
          $file->uuid(),
          $image_definition['uuid'],
        );
      }
      if ($file->getFileUri() !== $image_definition['uri']) {
        $errors[] = sprintf(
          'Article %02d delta %d URI is %s; expected %s.',
          $definition['number'],
          $delta,
          $file->getFileUri(),
          $image_definition['uri'],
        );
      }
      if (!$file->isPermanent()) {
        $errors[] = sprintf('Article %02d delta %d file is temporary.', $definition['number'], $delta);
      }

      $real_path = \Drupal::service('file_system')->realpath($file->getFileUri());
      if (!is_string($real_path) || !is_file($real_path)) {
        $errors[] = sprintf('Article %02d delta %d physical PNG is missing.', $definition['number'], $delta);
      }
      else {
        $dimensions = @getimagesize($real_path);
        if (!is_array($dimensions)
          || (int) ($dimensions[0] ?? 0) !== STEP9_IMAGE_WIDTH
          || (int) ($dimensions[1] ?? 0) !== STEP9_IMAGE_HEIGHT
          || (string) ($dimensions['mime'] ?? '') !== 'image/png') {
          $errors[] = sprintf(
            'Article %02d delta %d image is not the expected %dx%d PNG.',
            $definition['number'],
            $delta,
            STEP9_IMAGE_WIDTH,
            STEP9_IMAGE_HEIGHT,
          );
        }
      }

      $actual_alt = (string) $item->alt;
      if ($actual_alt !== (string) $image_definition['alt']) {
        $errors[] = sprintf(
          'Article %02d delta %d alt text is "%s"; expected "%s".',
          $definition['number'],
          $delta,
          $actual_alt,
          $image_definition['alt'],
        );
      }

      $classified_state = step9_classify_alt($actual_alt, $file->getFilename());
      if ($classified_state !== $image_definition['state']) {
        $errors[] = sprintf(
          'Article %02d delta %d classifies as %s; expected %s.',
          $definition['number'],
          $delta,
          $classified_state,
          $image_definition['state'],
        );
      }

      if ($classified_state === 'missing' || $classified_state === 'poor') {
        $node_has_target = TRUE;
        if ($classified_state === 'missing') {
          $missing_count++;
        }
        else {
          $poor_count++;
        }
        $manifest[] = [
          'article_number' => (int) $definition['number'],
          'title' => (string) $definition['title'],
          'node_id' => (int) $node->id(),
          'node_uuid' => $node->uuid(),
          'node_revision_id' => (int) $node->getRevisionId(),
          'field_name' => STEP9_IMAGE_FIELD,
          'delta' => $delta,
          'file_id' => (int) $file->id(),
          'file_uuid' => $file->uuid(),
          'file_uri' => $file->getFileUri(),
          'current_alt' => $actual_alt,
          'target_state' => $classified_state,
        ];
      }
    }

    if (!$node_has_target) {
      $acceptable_node_count++;
    }
  }

  sort($seed_node_ids);
  $seed_node_ids = array_values(array_unique($seed_node_ids));
  sort($seed_file_ids);
  $seed_file_ids = array_values(array_unique($seed_file_ids));

  if ($article_count !== STEP9_EXPECTED_ARTICLES) {
    $errors[] = sprintf('Found %d seed Articles; expected %d.', $article_count, STEP9_EXPECTED_ARTICLES);
  }
  if (count($seed_node_ids) !== STEP9_EXPECTED_ARTICLES) {
    $errors[] = sprintf('Found %d unique seed node IDs; expected %d.', count($seed_node_ids), STEP9_EXPECTED_ARTICLES);
  }
  if ($file_count !== STEP9_EXPECTED_FILES) {
    $errors[] = sprintf('Found %d image-field usages; expected %d.', $file_count, STEP9_EXPECTED_FILES);
  }
  if (count($seed_file_ids) !== STEP9_EXPECTED_FILES) {
    $errors[] = sprintf('Found %d unique seed files; expected %d.', count($seed_file_ids), STEP9_EXPECTED_FILES);
  }
  if (count($manifest) !== STEP9_EXPECTED_TARGETS) {
    $errors[] = sprintf('Found %d target usages; expected %d.', count($manifest), STEP9_EXPECTED_TARGETS);
  }
  if ($missing_count !== STEP9_EXPECTED_MISSING) {
    $errors[] = sprintf('Found %d missing-alt targets; expected %d.', $missing_count, STEP9_EXPECTED_MISSING);
  }
  if ($poor_count !== STEP9_EXPECTED_POOR) {
    $errors[] = sprintf('Found %d poor-alt targets; expected %d.', $poor_count, STEP9_EXPECTED_POOR);
  }
  if ($acceptable_node_count !== 8) {
    $errors[] = sprintf('Found %d fully acceptable Articles; expected 8.', $acceptable_node_count);
  }

  usort($manifest, static fn(array $a, array $b): int => [$a['article_number'], $a['delta']] <=> [$b['article_number'], $b['delta']]);

  if ($verbose) {
    step9_note(sprintf('Seed Articles: %d / %d', $article_count, STEP9_EXPECTED_ARTICLES));
    step9_note(sprintf('Generated PNG files: %d / %d', count($seed_file_ids), STEP9_EXPECTED_FILES));
    step9_note(sprintf('Target usages: %d / %d', count($manifest), STEP9_EXPECTED_TARGETS));
    step9_note(sprintf('Coverage: %d missing, %d poor, %d fully acceptable Articles', $missing_count, $poor_count, $acceptable_node_count));

    foreach ($manifest as $target) {
      step9_note(sprintf(
        'Target %02d: node %d rev %d · %s[%d] · file %d · %s',
        $target['article_number'],
        $target['node_id'],
        $target['node_revision_id'],
        $target['field_name'],
        $target['delta'],
        $target['file_id'],
        $target['target_state'],
      ));
    }
  }

  if ($errors !== []) {
    foreach ($errors as $error) {
      step9_error($error);
    }
    step9_fail(sprintf('Step 9 audit failed with %d issue(s).', count($errors)));
  }

  if ($verbose) {
    step9_ok('Step 9 audit passed. The deterministic 12-target manifest is valid.');
  }

  return $manifest;
}

/**
 * Prints the current target manifest as JSON and no informational prose.
 */
function step9_print_manifest(): void {
  $manifest = step9_audit(FALSE);
  $json = json_encode(
    [
      'schema_version' => 1,
      'seed_script_version' => STEP9_SCRIPT_VERSION,
      'target_count' => count($manifest),
      'targets' => $manifest,
    ],
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR,
  );
  fwrite(STDOUT, $json . PHP_EOL);
}

/**
 * Guardedly removes only Step 9 seed content and suggestions targeting it.
 */
function step9_remove(): void {
  $dataset = step9_dataset();
  $node_ids = [];
  $file_ids = [];

  foreach ($dataset as $definition) {
    /** @var \Drupal\node\NodeInterface|null $node */
    $node = step9_load_entity_by_uuid('node', (string) $definition['uuid']);
    if ($node !== NULL) {
      $node_ids[] = (int) $node->id();
      foreach ($node->get(STEP9_IMAGE_FIELD) as $item) {
        if ($item->target_id !== NULL) {
          $file_ids[] = (int) $item->target_id;
        }
      }
    }
  }

  $suggestion_count = 0;
  if ($node_ids !== [] && \Drupal::entityTypeManager()->getStorage('node_type')->load(STEP9_SUGGESTION_BUNDLE)) {
    $suggestion_ids = \Drupal::entityQuery('node')
      ->accessCheck(FALSE)
      ->condition('type', STEP9_SUGGESTION_BUNDLE)
      ->condition('field_target_node.target_id', $node_ids, 'IN')
      ->execute();
    if ($suggestion_ids !== []) {
      $suggestions = \Drupal::entityTypeManager()->getStorage('node')->loadMultiple($suggestion_ids);
      $suggestion_count = count($suggestions);
      \Drupal::entityTypeManager()->getStorage('node')->delete($suggestions);
    }
  }

  $node_count = 0;
  if ($node_ids !== []) {
    $nodes = \Drupal::entityTypeManager()->getStorage('node')->loadMultiple(array_unique($node_ids));
    $node_count = count($nodes);
    \Drupal::entityTypeManager()->getStorage('node')->delete($nodes);
  }

  $file_count = 0;
  $file_ids = array_values(array_unique($file_ids));
  if ($file_ids !== []) {
    $files = \Drupal::entityTypeManager()->getStorage('file')->loadMultiple($file_ids);
    foreach ($files as $file) {
      if (str_starts_with($file->getFileUri(), STEP9_FILE_DIRECTORY . '/')) {
        $file->delete();
        $file_count++;
      }
    }
  }

  step9_ok(sprintf(
    'Removed %d targeted suggestion records, %d seed Articles, and %d seed File entities.',
    $suggestion_count,
    $node_count,
    $file_count,
  ));
  step9_note('The Article bundle, fields, roles, accounts, and review queue were left intact.');
}

/**
 * Classifies alt text using deterministic Step 9 validation rules.
 */
function step9_classify_alt(string $alt, string $filename): string {
  $trimmed = trim($alt);
  if ($trimmed === '') {
    return 'missing';
  }

  $normalized = mb_strtolower($trimmed);
  $generic = ['photo', 'image', 'picture', 'image.jpg', 'image.png', 'photograph'];
  $filename_normalized = mb_strtolower(trim($filename));
  $filename_without_extension = mb_strtolower((string) pathinfo($filename, PATHINFO_FILENAME));

  if (in_array($normalized, $generic, TRUE)
    || $normalized === $filename_normalized
    || $normalized === $filename_without_extension) {
    return 'poor';
  }

  return 'acceptable';
}

/**
 * Creates a deterministic 1200x675 PNG using GD and block-number glyphs.
 *
 * @param array<string, mixed> $article_definition
 * @param array<string, mixed> $image_definition
 */
function step9_generate_png(array $article_definition, array $image_definition): string {
  $image = imagecreatetruecolor(STEP9_IMAGE_WIDTH, STEP9_IMAGE_HEIGHT);
  if ($image === FALSE) {
    step9_fail('GD could not create the seed image canvas.');
  }

  [$red, $green, $blue] = $image_definition['rgb'];
  $background = imagecolorallocate($image, (int) $red, (int) $green, (int) $blue);
  $brightness = ((int) $red * 299 + (int) $green * 587 + (int) $blue * 114) / 1000;
  $foreground = $brightness > 145
    ? imagecolorallocate($image, 15, 23, 42)
    : imagecolorallocate($image, 255, 255, 255);
  $accent = $brightness > 145
    ? imagecolorallocate($image, 30, 41, 59)
    : imagecolorallocate($image, 226, 232, 240);

  imagefilledrectangle($image, 0, 0, STEP9_IMAGE_WIDTH - 1, STEP9_IMAGE_HEIGHT - 1, $background);
  imagerectangle($image, 18, 18, STEP9_IMAGE_WIDTH - 19, STEP9_IMAGE_HEIGHT - 19, $foreground);
  imagerectangle($image, 25, 25, STEP9_IMAGE_WIDTH - 26, STEP9_IMAGE_HEIGHT - 26, $accent);

  $header = sprintf('PHASE 0 - %s IMAGE', $image_definition['slot'] === 1 ? 'PRIMARY' : 'SUPPORTING');
  $footer = strtoupper((string) $article_definition['topic']);
  imagestring($image, 5, 48, 48, $header, $foreground);
  imagestring($image, 5, 48, STEP9_IMAGE_HEIGHT - 72, $footer, $foreground);

  step9_draw_block_number(
    $image,
    (string) $article_definition['number'],
    STEP9_IMAGE_WIDTH,
    STEP9_IMAGE_HEIGHT,
    $foreground,
  );

  imagestring(
    $image,
    5,
    STEP9_IMAGE_WIDTH - 220,
    STEP9_IMAGE_HEIGHT - 72,
    sprintf('SLOT %d', $image_definition['slot']),
    $foreground,
  );

  ob_start();
  $written = imagepng($image, NULL, 9);
  $data = ob_get_clean();
  imagedestroy($image);

  if (!$written || !is_string($data) || $data === '') {
    step9_fail('GD failed to encode a generated PNG.');
  }

  return $data;
}

/**
 * Draws one- or two-digit article numbers using a built-in 5x7 bitmap font.
 *
 * @param \GdImage|resource $image
 */
function step9_draw_block_number($image, string $number, int $canvas_width, int $canvas_height, int $color): void {
  $glyphs = [
    '0' => ['11111', '10001', '10011', '10101', '11001', '10001', '11111'],
    '1' => ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2' => ['11111', '00001', '00001', '11111', '10000', '10000', '11111'],
    '3' => ['11111', '00001', '00001', '01111', '00001', '00001', '11111'],
    '4' => ['10001', '10001', '10001', '11111', '00001', '00001', '00001'],
    '5' => ['11111', '10000', '10000', '11111', '00001', '00001', '11111'],
    '6' => ['11111', '10000', '10000', '11111', '10001', '10001', '11111'],
    '7' => ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8' => ['11111', '10001', '10001', '11111', '10001', '10001', '11111'],
    '9' => ['11111', '10001', '10001', '11111', '00001', '00001', '11111'],
  ];

  $scale = 48;
  $pixel_gap = 5;
  $digit_gap = 42;
  $digit_width = (5 * $scale) + (4 * $pixel_gap);
  $digit_height = (7 * $scale) + (6 * $pixel_gap);
  $total_width = (strlen($number) * $digit_width) + ((strlen($number) - 1) * $digit_gap);
  $start_x = (int) (($canvas_width - $total_width) / 2);
  $start_y = (int) (($canvas_height - $digit_height) / 2) - 6;

  foreach (str_split($number) as $digit_index => $digit) {
    $glyph = $glyphs[$digit] ?? NULL;
    if ($glyph === NULL) {
      continue;
    }
    $digit_x = $start_x + ($digit_index * ($digit_width + $digit_gap));
    foreach ($glyph as $row => $row_data) {
      foreach (str_split($row_data) as $column => $bit) {
        if ($bit !== '1') {
          continue;
        }
        $x1 = $digit_x + ($column * ($scale + $pixel_gap));
        $y1 = $start_y + ($row * ($scale + $pixel_gap));
        imagefilledrectangle($image, $x1, $y1, $x1 + $scale - 1, $y1 + $scale - 1, $color);
      }
    }
  }
}

/**
 * Validates Step 7/8 prerequisites and runtime capabilities.
 */
function step9_require_environment(): void {
  $module_handler = \Drupal::moduleHandler();
  foreach (['node', 'file', 'image', 'text', 'filter'] as $module) {
    if (!$module_handler->moduleExists($module)) {
      step9_fail(sprintf('Required core module "%s" is not enabled.', $module));
    }
  }

  if (!extension_loaded('gd') || !function_exists('imagecreatetruecolor')) {
    step9_fail('The PHP GD extension is not available inside the DDEV web container.');
  }
  if (!function_exists('mb_strtolower')) {
    step9_fail('The PHP mbstring extension is required for deterministic alt-text validation.');
  }

  $type_storage = \Drupal::entityTypeManager()->getStorage('node_type');
  if ($type_storage->load(STEP9_ARTICLE_BUNDLE) === NULL) {
    step9_fail('Article does not exist. Run the corrected Phase 0 Step 8 script first.');
  }
  if ($type_storage->load(STEP9_SUGGESTION_BUNDLE) === NULL) {
    step9_fail('alt_text_suggestion does not exist. Run Phase 0 Step 8 first.');
  }

  $field_manager = \Drupal::service('entity_field.manager');
  $article_fields = $field_manager->getFieldDefinitions('node', STEP9_ARTICLE_BUNDLE);
  if (!isset($article_fields['body'])) {
    step9_fail('Article is missing the Body field required by Step 9.');
  }
  if (!isset($article_fields[STEP9_IMAGE_FIELD])) {
    step9_fail(sprintf('Article is missing %s. Run Phase 0 Step 8 first.', STEP9_IMAGE_FIELD));
  }
  $cardinality = $article_fields[STEP9_IMAGE_FIELD]->getFieldStorageDefinition()->getCardinality();
  if ($cardinality !== -1 && $cardinality < 2) {
    step9_fail(sprintf('%s cardinality is %d; Step 9 requires at least 2.', STEP9_IMAGE_FIELD, $cardinality));
  }

  step9_load_required_user('editor_dana');
  step9_default_text_format();
  step9_validate_dataset_definition();
}

/**
 * Returns the default available text format ID.
 */
function step9_default_text_format(): string {
  $format_storage = \Drupal::entityTypeManager()->getStorage('filter_format');
  $plain_text = $format_storage->load('plain_text');
  if ($plain_text !== NULL && $plain_text->status()) {
    return 'plain_text';
  }

  $default = \Drupal::service('filter.format_repository')->getDefaultFormat();
  if ($default !== NULL && $default->status()) {
    return $default->id();
  }

  step9_fail('No enabled Drupal text format is available for the seeded Article bodies.');
}

/**
 * Loads a required active user by exact username.
 */
function step9_load_required_user(string $username): \Drupal\user\UserInterface {
  $ids = \Drupal::entityQuery('user')
    ->accessCheck(FALSE)
    ->condition('name', $username)
    ->execute();
  if (count($ids) !== 1) {
    step9_fail(sprintf('Expected exactly one user named %s; found %d.', $username, count($ids)));
  }
  /** @var \Drupal\user\UserInterface|null $user */
  $user = \Drupal::entityTypeManager()->getStorage('user')->load((int) reset($ids));
  if ($user === NULL || !$user->isActive()) {
    step9_fail(sprintf('Required user %s is missing or blocked.', $username));
  }
  return $user;
}

/**
 * Validates the in-code fixture before touching Drupal content.
 */
function step9_validate_dataset_definition(): void {
  $dataset = step9_dataset();
  $article_count = count($dataset);
  $file_count = 0;
  $target_count = 0;
  $missing_count = 0;
  $poor_count = 0;
  $acceptable_nodes = 0;
  $node_uuids = [];
  $file_uuids = [];
  $uris = [];

  foreach ($dataset as $definition) {
    $node_uuids[] = $definition['uuid'];
    $node_has_target = FALSE;
    $image_count = count($definition['images']);
    if (!in_array($image_count, [1, 2], TRUE)) {
      step9_fail(sprintf('Article %02d has %d defined images; expected one or two.', $definition['number'], $image_count));
    }

    foreach ($definition['images'] as $image) {
      $file_count++;
      $file_uuids[] = $image['uuid'];
      $uris[] = $image['uri'];
      if ($image['state'] === 'missing' || $image['state'] === 'poor') {
        $node_has_target = TRUE;
        $target_count++;
        $missing_count += $image['state'] === 'missing' ? 1 : 0;
        $poor_count += $image['state'] === 'poor' ? 1 : 0;
      }
    }
    if (!$node_has_target) {
      $acceptable_nodes++;
    }
  }

  $checks = [
    ['Articles', $article_count, STEP9_EXPECTED_ARTICLES],
    ['files', $file_count, STEP9_EXPECTED_FILES],
    ['targets', $target_count, STEP9_EXPECTED_TARGETS],
    ['missing targets', $missing_count, STEP9_EXPECTED_MISSING],
    ['poor targets', $poor_count, STEP9_EXPECTED_POOR],
    ['fully acceptable Articles', $acceptable_nodes, 8],
  ];
  foreach ($checks as [$label, $actual, $expected]) {
    if ($actual !== $expected) {
      step9_fail(sprintf('In-code fixture defines %d %s; expected %d.', $actual, $label, $expected));
    }
  }
  if (count(array_unique($node_uuids)) !== count($node_uuids)) {
    step9_fail('In-code fixture contains duplicate node UUIDs.');
  }
  if (count(array_unique($file_uuids)) !== count($file_uuids)) {
    step9_fail('In-code fixture contains duplicate file UUIDs.');
  }
  if (count(array_unique($uris)) !== count($uris)) {
    step9_fail('In-code fixture contains duplicate file URIs.');
  }
}

/**
 * Loads all Article nodes with an exact title, bypassing access checks.
 *
 * @return array<int, \Drupal\node\NodeInterface>
 */
function step9_load_nodes_by_title(string $title): array {
  $ids = \Drupal::entityQuery('node')
    ->accessCheck(FALSE)
    ->condition('type', STEP9_ARTICLE_BUNDLE)
    ->condition('title', $title)
    ->execute();
  /** @var array<int, \Drupal\node\NodeInterface> $nodes */
  $nodes = \Drupal::entityTypeManager()->getStorage('node')->loadMultiple($ids);
  return $nodes;
}

/**
 * Loads one entity by UUID and fails on duplicate UUID results.
 */
function step9_load_entity_by_uuid(string $entity_type, string $uuid): ?\Drupal\Core\Entity\EntityInterface {
  $ids = \Drupal::entityQuery($entity_type)
    ->accessCheck(FALSE)
    ->condition('uuid', $uuid)
    ->execute();
  if (count($ids) > 1) {
    step9_fail(sprintf('UUID %s resolves to multiple %s entities.', $uuid, $entity_type));
  }
  if ($ids === []) {
    return NULL;
  }
  return \Drupal::entityTypeManager()->getStorage($entity_type)->load((int) reset($ids));
}

/**
 * Loads one File entity by URI and fails on duplicates.
 */
function step9_load_file_by_uri(string $uri): ?\Drupal\file\FileInterface {
  $ids = \Drupal::entityQuery('file')
    ->accessCheck(FALSE)
    ->condition('uri', $uri)
    ->execute();
  if (count($ids) > 1) {
    step9_fail(sprintf('URI %s resolves to multiple File entities.', $uri));
  }
  if ($ids === []) {
    return NULL;
  }
  /** @var \Drupal\file\FileInterface|null $file */
  $file = \Drupal::entityTypeManager()->getStorage('file')->load((int) reset($ids));
  return $file;
}

/**
 * Generates a deterministic UUIDv5.
 */
function step9_uuid_v5(string $namespace, string $name): string {
  $namespace_hex = str_replace(['-', '{', '}'], '', $namespace);
  if (strlen($namespace_hex) !== 32 || !ctype_xdigit($namespace_hex)) {
    throw new InvalidArgumentException('Invalid UUID namespace.');
  }

  $namespace_bytes = '';
  for ($i = 0; $i < 32; $i += 2) {
    $namespace_bytes .= chr((int) hexdec(substr($namespace_hex, $i, 2)));
  }

  $hash = sha1($namespace_bytes . $name);
  $time_hi = (hexdec(substr($hash, 12, 4)) & 0x0fff) | 0x5000;
  $clock_seq = (hexdec(substr($hash, 16, 4)) & 0x3fff) | 0x8000;

  return sprintf(
    '%s-%s-%04x-%04x-%s',
    substr($hash, 0, 8),
    substr($hash, 8, 4),
    $time_hi,
    $clock_seq,
    substr($hash, 20, 12),
  );
}

function step9_note(string $message): void {
  fwrite(STDOUT, '[INFO] ' . $message . PHP_EOL);
}

function step9_ok(string $message): void {
  fwrite(STDOUT, '[OK] ' . $message . PHP_EOL);
}

function step9_error(string $message): void {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
}

function step9_fail(string $message): never {
  step9_error($message);
  exit(1);
}
