<?php

declare(strict_types=1);

/**
 * Safe inspection helper for Gate 0.5 Step 03 evidence.
 *
 * Usage:
 *   ddev drush --quiet php:script scripts/gate05-step03.php -- inspect <nid>
 *   ddev drush --quiet php:script scripts/gate05-step03.php -- snapshot
 */

use Drupal\node\NodeInterface;
use Drupal\file\FileInterface;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';
$node_id = isset($args[1]) ? (int) $args[1] : 0;

$storage = \Drupal::entityTypeManager()->getStorage('node');

if ($mode === 'snapshot') {
  $article_ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->sort('nid', 'ASC')
    ->execute();

  $articles = [];
  foreach ($storage->loadMultiple($article_ids) as $article) {
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
    $articles[] = [
      'node_uuid' => $article->uuid(),
      'revision_id' => (int) $article->getRevisionId(),
      'title' => (string) $article->label(),
      'status' => (bool) $article->isPublished(),
      'images' => $images,
    ];
  }

  $suggestion_count = (int) $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->count()
    ->execute();

  $canonical_articles = gate05_step03_canonicalize($articles);
  $article_json = json_encode(
    $canonical_articles,
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );
  $combined_json = json_encode(
    gate05_step03_canonicalize([
      'articles' => $articles,
      'suggestion_count' => $suggestion_count,
    ]),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  );

  print json_encode([
    'helper_version' => '1.0.1',
    'mode' => 'snapshot',
    'status' => 'pass',
    'article_count' => count($articles),
    'article_source_sha256' => hash('sha256', $article_json),
    'suggestion_count' => $suggestion_count,
    'combined_state_sha256' => hash('sha256', $combined_json),
  ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;
  return;
}

if ($mode !== 'inspect' || $node_id < 1) {
  fwrite(STDERR, "[ERROR] Use: inspect <node ID> or snapshot\n");
  exit(1);
}

$node = $storage->load($node_id);
if (!$node instanceof NodeInterface || $node->bundle() !== 'alt_text_suggestion') {
  fwrite(STDERR, "[ERROR] Recommendation node not found.\n");
  exit(1);
}

$target_node = $node->get('field_target_node')->entity;
$target_file = $node->get('field_target_file')->entity;
if (!$target_node instanceof NodeInterface || !$target_file instanceof FileInterface) {
  fwrite(STDERR, "[ERROR] Recommendation target references are incomplete.\n");
  exit(1);
}

$identity_ids = $storage->getQuery()
  ->accessCheck(FALSE)
  ->condition('type', 'alt_text_suggestion')
  ->condition('field_source_framework.value', (string) $node->get('field_source_framework')->value)
  ->condition('field_run_id.value', (string) $node->get('field_run_id')->value)
  ->condition('field_target_node.target_id', (int) $target_node->id())
  ->condition('field_target_revision.value', (int) $node->get('field_target_revision')->value)
  ->condition('field_target_field.value', (string) $node->get('field_target_field')->value)
  ->condition('field_target_delta.value', (int) $node->get('field_target_delta')->value)
  ->condition('field_target_file.target_id', (int) $target_file->id())
  ->execute();

$total_count = (int) $storage->getQuery()
  ->accessCheck(FALSE)
  ->condition('type', 'alt_text_suggestion')
  ->count()
  ->execute();

$owner = $node->getOwner();

print json_encode([
  'node_id' => (int) $node->id(),
  'uuid' => $node->uuid(),
  'revision_id' => (int) $node->getRevisionId(),
  'published' => $node->isPublished(),
  'owner_username' => $owner?->getAccountName(),
  'title' => (string) $node->label(),
  'review_status' => (string) $node->get('field_review_status')->value,
  'source_framework' => (string) $node->get('field_source_framework')->value,
  'run_id' => (string) $node->get('field_run_id')->value,
  'evidence_hash' => (string) $node->get('field_evidence_hash')->value,
  'proposed_alt_text' => (string) $node->get('field_proposed_alt')->value,
  'revision_log' => (string) $node->getRevisionLogMessage(),
  'target' => [
    'node_uuid' => $target_node->uuid(),
    'revision_id' => (int) $node->get('field_target_revision')->value,
    'field_name' => (string) $node->get('field_target_field')->value,
    'delta' => (int) $node->get('field_target_delta')->value,
    'file_uuid' => $target_file->uuid(),
  ],
  'identity_count' => count($identity_ids),
  'total_suggestion_count' => $total_count,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;


/**
 * Canonically sorts nested arrays for stable hashing.
 */
function gate05_step03_canonicalize(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('gate05_step03_canonicalize', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = gate05_step03_canonicalize($item);
  }
  return $value;
}
