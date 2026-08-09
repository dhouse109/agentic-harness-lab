<?php

declare(strict_types=1);

/**
 * Read-only Step 1.06 helper.
 *
 * Usage:
 *   ddev drush --quiet php:script scripts/gate1-step06-human-review.php -- counts <run-id>
 *   ddev drush --quiet php:script scripts/gate1-step06-human-review.php -- reviewer
 */

use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';

if ($mode === 'reviewer') {
  $matches = \Drupal::entityTypeManager()->getStorage('user')->loadByProperties(['name' => 'editor_dana']);
  $user = $matches === [] ? NULL : reset($matches);
  if (!$user instanceof UserInterface) {
    fwrite(STDERR, "[ERROR] editor_dana not found.\n");
    exit(1);
  }
  print json_encode([
    'status' => 'pass',
    'username' => $user->getAccountName(),
    'uid' => (int) $user->id(),
    'active' => $user->isActive(),
    'roles' => array_values($user->getRoles()),
  ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;
  return;
}

if ($mode !== 'counts' || !isset($args[1]) || trim($args[1]) === '') {
  fwrite(STDERR, "[ERROR] Use: counts <run-id> or reviewer\n");
  exit(1);
}

$run_id = trim($args[1]);
$storage = \Drupal::entityTypeManager()->getStorage('node');
$ids = $storage->getQuery()
  ->accessCheck(FALSE)
  ->condition('type', 'alt_text_suggestion')
  ->condition('field_run_id', $run_id)
  ->sort('nid', 'ASC')
  ->execute();

$counts = ['pending' => 0, 'approved' => 0, 'rejected' => 0];
$records = [];
foreach ($storage->loadMultiple($ids) as $node) {
  if (!$node instanceof NodeInterface) {
    continue;
  }
  $status = (string) $node->get('field_review_status')->value;
  if (!array_key_exists($status, $counts)) {
    fwrite(STDERR, "[ERROR] Unexpected review status.\n");
    exit(1);
  }
  $counts[$status]++;
  $target = $node->get('field_target_node')->entity;
  $sequence = NULL;
  if ($target instanceof NodeInterface) {
    $title = (string) $target->label();
    if (preg_match('/(\d{2})$/', $title, $matches) === 1) {
      $sequence = (int) $matches[1];
    }
  }
  $records[] = [
    'node_id' => (int) $node->id(),
    'uuid' => $node->uuid(),
    'revision_id' => (int) $node->getRevisionId(),
    'status' => $status,
    'run_id' => (string) $node->get('field_run_id')->value,
    'source_framework' => (string) $node->get('field_source_framework')->value,
    'target_node_uuid' => $target instanceof NodeInterface ? $target->uuid() : NULL,
    'sequence_hint' => $sequence,
  ];
}

print json_encode([
  'status' => 'pass',
  'run_id' => $run_id,
  'total' => count($records),
  'counts' => $counts,
  'records' => $records,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL;
