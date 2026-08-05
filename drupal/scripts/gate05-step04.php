<?php

declare(strict_types=1);

/**
 * Read-only inspection and state hashing for Gate 0.5 Step 04.
 *
 * Usage:
 *   ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
 *   ddev drush --quiet php:script scripts/gate05-step04.php -- inspect <nid>
 */

use Drupal\Core\Entity\RevisionableStorageInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';
$node_id = isset($args[1]) ? (int) $args[1] : 0;

$entity_type_manager = \Drupal::entityTypeManager();
$node_storage = $entity_type_manager->getStorage('node');

if ($mode === 'snapshot') {
  gate05_step04_emit(gate05_step04_snapshot());
  return;
}

if ($mode !== 'inspect' || $node_id < 1) {
  fwrite(STDERR, "[ERROR] Use: snapshot or inspect <recommendation node ID>\n");
  exit(1);
}

if (!$node_storage instanceof RevisionableStorageInterface) {
  fwrite(STDERR, "[ERROR] Node storage is not revisionable.\n");
  exit(1);
}

$node = $node_storage->load($node_id);
if (!$node instanceof NodeInterface || $node->bundle() !== 'alt_text_suggestion') {
  fwrite(STDERR, "[ERROR] Recommendation node not found.\n");
  exit(1);
}

$revision_ids = \Drupal::database()->select('node_revision', 'nr')
  ->fields('nr', ['vid'])
  ->condition('nid', $node_id)
  ->orderBy('vid', 'ASC')
  ->execute()
  ->fetchCol();

$revisions = [];
foreach ($revision_ids as $revision_id) {
  $revision = $node_storage->loadRevision((int) $revision_id);
  if (!$revision instanceof NodeInterface) {
    fwrite(STDERR, "[ERROR] Unable to load recommendation revision.\n");
    exit(1);
  }

  $revision_user = gate05_step04_load_user_by_id(
    (int) $revision->getRevisionUserId(),
  );
  $target_node_id = (int) $revision->get('field_target_node')->target_id;
  $target_file_id = (int) $revision->get('field_target_file')->target_id;
  $target_node = $node_storage->load($target_node_id);
  $target_file = $entity_type_manager->getStorage('file')->load($target_file_id);

  if (!$target_node instanceof NodeInterface || !$target_file instanceof FileInterface) {
    fwrite(STDERR, "[ERROR] Recommendation target references are incomplete.\n");
    exit(1);
  }

  $revisions[] = [
    'revision_id' => (int) $revision->getRevisionId(),
    'revision_user' => [
      'uid' => (int) $revision_user->id(),
      'name' => $revision_user->getAccountName(),
    ],
    'timestamp_unix' => (int) $revision->getRevisionCreationTime(),
    'timestamp_utc' => gmdate(
      'Y-m-d\TH:i:s\Z',
      (int) $revision->getRevisionCreationTime(),
    ),
    'revision_log' => (string) ($revision->getRevisionLogMessage() ?? ''),
    'published' => $revision->isPublished(),
    'proposed_alt_text' => (string) $revision->get('field_proposed_alt')->value,
    'review_status' => (string) $revision->get('field_review_status')->value,
    'source_framework' => (string) $revision->get('field_source_framework')->value,
    'run_id' => (string) $revision->get('field_run_id')->value,
    'evidence_hash' => (string) $revision->get('field_evidence_hash')->value,
    'target' => [
      'node_id' => $target_node_id,
      'node_uuid' => $target_node->uuid(),
      'revision_id' => (int) $revision->get('field_target_revision')->value,
      'field_name' => (string) $revision->get('field_target_field')->value,
      'delta' => (int) $revision->get('field_target_delta')->value,
      'file_id' => $target_file_id,
      'file_uuid' => $target_file->uuid(),
    ],
  ];
}

$owner = gate05_step04_load_user_by_id((int) $node->getOwnerId());
$agent = gate05_step04_load_user_by_name('agent_bot');
$editor = gate05_step04_load_user_by_name('editor_dana');
$current = $revisions[count($revisions) - 1] ?? NULL;

if (!is_array($current)) {
  fwrite(STDERR, "[ERROR] Recommendation has no inspectable revision.\n");
  exit(1);
}

gate05_step04_emit([
  'helper_version' => '1.0.0',
  'mode' => 'inspect',
  'status' => 'pass',
  'node_id' => (int) $node->id(),
  'uuid' => $node->uuid(),
  'title' => (string) $node->label(),
  'owner_username' => $owner->getAccountName(),
  'published' => $node->isPublished(),
  'revision_count' => count($revisions),
  'current_revision_id' => (int) $node->getRevisionId(),
  'current_review_status' => $current['review_status'],
  'current_proposed_alt_text' => $current['proposed_alt_text'],
  'current_source_framework' => $current['source_framework'],
  'current_run_id' => $current['run_id'],
  'current_evidence_hash' => $current['evidence_hash'],
  'current_target' => $current['target'],
  'access' => [
    'agent_can_view' => $node->access('view', $agent),
    'agent_can_update' => $node->access('update', $agent),
    'editor_can_update' => $node->access('update', $editor),
  ],
  'revisions' => $revisions,
]);

/**
 * @return array<string, mixed>
 */
function gate05_step04_snapshot(): array {
  $entity_type_manager = \Drupal::entityTypeManager();
  $node_storage = $entity_type_manager->getStorage('node');

  $article_ids = $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->sort('nid', 'ASC')
    ->execute();

  $articles = [];
  foreach ($node_storage->loadMultiple($article_ids) as $article) {
    if (!$article instanceof NodeInterface) {
      continue;
    }

    $images = [];
    if ($article->hasField('field_image')) {
      foreach ($article->get('field_image') as $delta => $item) {
        $file = $item->entity;
        $images[] = [
          'delta' => (int) $delta,
          'file_uuid' => $file instanceof FileInterface ? $file->uuid() : NULL,
          'alt' => isset($item->alt) ? (string) $item->alt : '',
          'title' => isset($item->title) ? (string) $item->title : '',
        ];
      }
    }

    $body = [
      'value' => '',
      'summary' => '',
      'format' => NULL,
    ];
    if ($article->hasField('body') && !$article->get('body')->isEmpty()) {
      $body_item = $article->get('body')->first();
      $body = [
        'value' => (string) ($body_item?->value ?? ''),
        'summary' => (string) ($body_item?->summary ?? ''),
        'format' => $body_item?->format,
      ];
    }

    $articles[] = [
      'node_uuid' => $article->uuid(),
      'revision_id' => (int) $article->getRevisionId(),
      'title' => (string) $article->label(),
      'status' => $article->isPublished(),
      'body' => $body,
      'images' => $images,
    ];
  }

  $suggestion_ids = $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->sort('nid', 'ASC')
    ->execute();

  $suggestions = [];
  foreach ($node_storage->loadMultiple($suggestion_ids) as $suggestion) {
    if (!$suggestion instanceof NodeInterface) {
      continue;
    }

    $owner = gate05_step04_load_user_by_id((int) $suggestion->getOwnerId());
    $revision_user = gate05_step04_load_user_by_id(
      (int) $suggestion->getRevisionUserId(),
    );
    $target_node = $suggestion->get('field_target_node')->entity;
    $target_file = $suggestion->get('field_target_file')->entity;

    if (!$target_node instanceof NodeInterface || !$target_file instanceof FileInterface) {
      throw new RuntimeException('Suggestion target references are incomplete.');
    }

    $suggestions[] = [
      'uuid' => $suggestion->uuid(),
      'revision_id' => (int) $suggestion->getRevisionId(),
      'revision_user' => $revision_user->getAccountName(),
      'revision_timestamp' => (int) $suggestion->getRevisionCreationTime(),
      'owner' => $owner->getAccountName(),
      'published' => $suggestion->isPublished(),
      'proposed_alt_text' => (string) $suggestion->get('field_proposed_alt')->value,
      'review_status' => (string) $suggestion->get('field_review_status')->value,
      'source_framework' => (string) $suggestion->get('field_source_framework')->value,
      'run_id' => (string) $suggestion->get('field_run_id')->value,
      'evidence_hash' => (string) $suggestion->get('field_evidence_hash')->value,
      'target' => [
        'node_uuid' => $target_node->uuid(),
        'revision_id' => (int) $suggestion->get('field_target_revision')->value,
        'field_name' => (string) $suggestion->get('field_target_field')->value,
        'delta' => (int) $suggestion->get('field_target_delta')->value,
        'file_uuid' => $target_file->uuid(),
      ],
    ];
  }

  $canonical_articles = gate05_step04_canonicalize($articles);
  $canonical_suggestions = gate05_step04_canonicalize($suggestions);

  $article_json = json_encode(
    $canonical_articles,
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
  $suggestion_json = json_encode(
    $canonical_suggestions,
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
  $combined_json = json_encode(
    gate05_step04_canonicalize([
      'articles' => $articles,
      'suggestions' => $suggestions,
    ]),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );

  return [
    'helper_version' => '1.0.0',
    'mode' => 'snapshot',
    'status' => 'pass',
    'article_count' => count($articles),
    'article_source_sha256' => hash('sha256', $article_json),
    'suggestion_count' => count($suggestions),
    'recommendation_state_sha256' => hash('sha256', $suggestion_json),
    'combined_state_sha256' => hash('sha256', $combined_json),
  ];
}

function gate05_step04_load_user_by_name(string $name): UserInterface {
  $matches = \Drupal::entityTypeManager()
    ->getStorage('user')
    ->loadByProperties(['name' => $name]);
  $user = $matches === [] ? NULL : reset($matches);
  if (!$user instanceof UserInterface) {
    throw new RuntimeException('Required user not found: ' . $name);
  }
  return $user;
}

function gate05_step04_load_user_by_id(int $uid): UserInterface {
  $user = \Drupal::entityTypeManager()
    ->getStorage('user')
    ->load($uid);
  if (!$user instanceof UserInterface) {
    throw new RuntimeException('Required revision user not found.');
  }
  return $user;
}

function gate05_step04_canonicalize(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate05_step04_canonicalize', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate05_step04_canonicalize($item);
  }
  return $value;
}

function gate05_step04_emit(array $value): void {
  print json_encode(
    $value,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL;
}
