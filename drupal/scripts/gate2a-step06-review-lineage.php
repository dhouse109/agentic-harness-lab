<?php

declare(strict_types=1);

/** Read-only lineage audit for Gate 2A Step 2A.06. */

use Drupal\Core\Entity\RevisionableStorageInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? '';
$run_id = trim((string) ($args[1] ?? ''));
if (!in_array($mode, ['pending', 'reviewed'], TRUE) || $run_id === '') {
  fwrite(STDERR, "[ERROR] Use: pending <run-id> or reviewed <run-id>\n");
  exit(1);
}

$storage = \Drupal::entityTypeManager()->getStorage('node');
if (!$storage instanceof RevisionableStorageInterface) {
  fwrite(STDERR, "[ERROR] Node storage is not revisionable.\n");
  exit(1);
}
$ids = $storage->getQuery()
  ->accessCheck(FALSE)
  ->condition('type', 'alt_text_suggestion')
  ->condition('field_run_id', $run_id)
  ->condition('field_source_framework', 'langgraph')
  ->execute();
if (count($ids) !== 1) {
  fwrite(STDERR, sprintf("[ERROR] Expected exactly one Step 2A.06 recommendation; found %d.\n", count($ids)));
  exit(1);
}
$node = $storage->load((int) reset($ids));
if (!$node instanceof NodeInterface) {
  fwrite(STDERR, "[ERROR] Recommendation node could not be loaded.\n");
  exit(1);
}
$vids = \Drupal::database()->select('node_revision', 'nr')
  ->fields('nr', ['vid'])
  ->condition('nid', (int) $node->id())
  ->orderBy('vid', 'ASC')
  ->execute()
  ->fetchCol();
$revisions = [];
foreach ($vids as $vid) {
  $rev = $storage->loadRevision((int) $vid);
  if (!$rev instanceof NodeInterface) {
    fwrite(STDERR, "[ERROR] Recommendation revision could not be loaded.\n");
    exit(1);
  }
  $user = \Drupal::entityTypeManager()->getStorage('user')->load((int) $rev->getRevisionUserId());
  if (!$user instanceof UserInterface) {
    fwrite(STDERR, "[ERROR] Revision user could not be loaded.\n");
    exit(1);
  }
  $target = $rev->get('field_target_node')->entity;
  $file = $rev->get('field_target_file')->entity;
  if (!$target instanceof NodeInterface || $file === NULL) {
    fwrite(STDERR, "[ERROR] Target references are incomplete.\n");
    exit(1);
  }
  $revisions[] = [
    'revision_id' => (int) $rev->getRevisionId(),
    'revision_user' => ['uid' => (int) $user->id(), 'name' => $user->getAccountName()],
    'timestamp_unix' => (int) $rev->getRevisionCreationTime(),
    'timestamp_utc' => gmdate('c', (int) $rev->getRevisionCreationTime()),
    'revision_log' => (string) ($rev->getRevisionLogMessage() ?? ''),
    'proposed_alt' => (string) $rev->get('field_proposed_alt')->value,
    'review_status' => (string) $rev->get('field_review_status')->value,
    'source_framework' => (string) $rev->get('field_source_framework')->value,
    'run_id' => (string) $rev->get('field_run_id')->value,
    'evidence_hash' => (string) $rev->get('field_evidence_hash')->value,
    'target_node_uuid' => $target->uuid(),
    'target_revision' => (int) $rev->get('field_target_revision')->value,
    'target_field' => (string) $rev->get('field_target_field')->value,
    'target_delta' => (int) $rev->get('field_target_delta')->value,
    'target_file_uuid' => $file->uuid(),
  ];
}
if ($revisions === []) {
  fwrite(STDERR, "[ERROR] No recommendation revisions exist.\n");
  exit(1);
}
$first = $revisions[0];
$latest = $revisions[count($revisions) - 1];
$immutable = ['source_framework','run_id','evidence_hash','target_node_uuid','target_revision','target_field','target_delta','target_file_uuid'];
foreach ($revisions as $rev) {
  foreach ($immutable as $key) {
    if ($rev[$key] !== $first[$key]) {
      fwrite(STDERR, sprintf("[ERROR] Immutable field %s changed through review.\n", $key));
      exit(1);
    }
  }
}
if ($first['revision_user']['name'] !== 'agent_bot' || $first['review_status'] !== 'pending') {
  fwrite(STDERR, "[ERROR] Initial revision is not pending agent_bot provenance.\n");
  exit(1);
}
if ($mode === 'pending') {
  if (count($revisions) !== 1 || $latest['review_status'] !== 'pending') {
    fwrite(STDERR, "[ERROR] Pending boundary has unexpected review history.\n");
    exit(1);
  }
}
else {
  if (count($revisions) !== 2) {
    fwrite(STDERR, sprintf("[ERROR] Edit-and-approve proof requires exactly two revisions; found %d.\n", count($revisions)));
    exit(1);
  }
  if ($latest['revision_user']['name'] !== 'editor_dana' || $latest['review_status'] !== 'approved') {
    fwrite(STDERR, "[ERROR] Latest revision is not an editor_dana approval.\n");
    exit(1);
  }
  $edited = trim((string) $latest['proposed_alt']);
  if ($edited === '' || mb_strlen($edited) > 250 || $edited === $first['proposed_alt']) {
    fwrite(STDERR, "[ERROR] Reviewer did not make one valid proposed-alt edit.\n");
    exit(1);
  }
}

print json_encode([
  'schema_version' => 1,
  'status' => 'pass',
  'audit_state' => $mode,
  'run_id' => $run_id,
  'node_id' => (int) $node->id(),
  'node_uuid' => $node->uuid(),
  'revision_count' => count($revisions),
  'revisions' => $revisions,
  'paths' => [
    'view' => '/node/' . $node->id(),
    'edit' => '/node/' . $node->id() . '/edit',
    'history' => '/node/' . $node->id() . '/revisions',
  ],
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . PHP_EOL;
