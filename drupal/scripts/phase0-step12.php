<?php

declare(strict_types=1);

/**
 * Phase 0, Step 12: revision-inspectability fixtures and assertions.
 *
 * Commands:
 *   ddev drush php:script scripts/phase0-step12.php -- preflight
 *   ddev drush php:script scripts/phase0-step12.php -- prepare
 *   ddev drush php:script scripts/phase0-step12.php -- audit-pending
 *   ddev drush php:script scripts/phase0-step12.php -- audit-reviewed
 *   ddev drush php:script scripts/phase0-step12.php -- json-pending
 *   ddev drush php:script scripts/phase0-step12.php -- json-reviewed
 *
 * The prepare command creates three pending suggestions as agent_bot. The
 * reviewer decisions themselves are intentionally completed through Drupal's
 * UI as editor_dana so Step 12 proves the real editorial workflow.
 */

use Drupal\Core\Entity\RevisionableStorageInterface;
use Drupal\node\Entity\Node;
use Drupal\node\NodeInterface;
use Drupal\user\RoleInterface;
use Drupal\user\UserInterface;

const STEP12_HELPER_VERSION = '1.0.1';
const STEP12_BUNDLE = 'alt_text_suggestion';
const STEP12_RUN_ID = 'phase0-step12-revision-inspectability';
const STEP12_NAMESPACE_UUID = 'ecfbaafa-4f39-5bc1-a6b5-c04994e6eb9e';

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? 'preflight';
$allowed_modes = [
  'preflight',
  'prepare',
  'audit-pending',
  'audit-reviewed',
  'json-pending',
  'json-reviewed',
];

if (!in_array($mode, $allowed_modes, TRUE)) {
  step12_fail(sprintf(
    'Unknown mode "%s". Use: %s.',
    $mode,
    implode(', ', $allowed_modes),
  ));
}

$json_mode = str_starts_with($mode, 'json-');
if (!$json_mode) {
  step12_note('Step 12 helper version: ' . STEP12_HELPER_VERSION);
}

step12_require_environment();

switch ($mode) {
  case 'preflight':
    step12_preflight();
    break;

  case 'prepare':
    step12_prepare();
    step12_audit('pending', TRUE);
    break;

  case 'audit-pending':
    step12_audit('pending', TRUE);
    break;

  case 'audit-reviewed':
    step12_audit('reviewed', TRUE);
    break;

  case 'json-pending':
    step12_emit_json('pending');
    break;

  case 'json-reviewed':
    step12_emit_json('reviewed');
    break;
}

/**
 * Defines the three deterministic review cases.
 *
 * @return array<int, array<string, mixed>>
 */
function step12_case_definitions(): array {
  return [
    [
      'case_id' => 'A',
      'title' => 'Step 12 A — Approve unchanged',
      'action' => 'Approve unchanged',
      'article_title' => 'Phase 0 01 — Emergency Preparedness Checklist',
      'article_number' => 1,
      'delta' => 0,
      'source_origin' => 'phase0_fixture',
      'initial_alt' => 'Navy demonstration placard labeled Article 1 for emergency preparedness.',
      'expected_status' => 'approved',
      'expected_alt' => 'Navy demonstration placard labeled Article 1 for emergency preparedness.',
      'review_instruction' => 'Set Review status to Approved. Do not change Proposed alt text.',
    ],
    [
      'case_id' => 'B',
      'title' => 'Step 12 B — Reject',
      'action' => 'Reject',
      'article_title' => 'Phase 0 02 — Community Grant Application Guide',
      'article_number' => 2,
      'delta' => 1,
      'source_origin' => 'phase0_fixture',
      'initial_alt' => 'Teal demonstration placard labeled Article 2 for community grants supporting context.',
      'expected_status' => 'rejected',
      'expected_alt' => 'Teal demonstration placard labeled Article 2 for community grants supporting context.',
      'review_instruction' => 'Set Review status to Rejected. Do not change Proposed alt text.',
    ],
    [
      'case_id' => 'C',
      'title' => 'Step 12 C — Edit and approve',
      'action' => 'Edit and approve',
      'article_title' => 'Phase 0 03 — Public Meeting Accessibility Notice',
      'article_number' => 3,
      'delta' => 0,
      'source_origin' => 'phase0_fixture',
      'initial_alt' => 'Public meeting image for Article 3.',
      'expected_status' => 'approved',
      'expected_alt' => 'Maroon demonstration placard labeled Article 3 for accessible public meetings.',
      'review_instruction' => 'Replace Proposed alt text with the exact expected text, set Review status to Approved, and save.',
    ],
  ];
}

/**
 * Verifies bundles, fields, roles, permissions, users, and target Articles.
 */
function step12_require_environment(): void {
  $entity_type_manager = \Drupal::entityTypeManager();
  $node_type_storage = $entity_type_manager->getStorage('node_type');

  $suggestion_type = $node_type_storage->load(STEP12_BUNDLE);
  if ($suggestion_type === NULL) {
    step12_fail('Missing alt_text_suggestion content type. Complete Step 8 first.');
  }
  if (!$suggestion_type->shouldCreateNewRevision()) {
    step12_fail('alt_text_suggestion is not configured to create a new revision on each save.');
  }

  $field_manager = \Drupal::service('entity_field.manager');
  $fields = $field_manager->getFieldDefinitions('node', STEP12_BUNDLE);
  foreach ([
    'field_target_node',
    'field_target_revision',
    'field_target_field',
    'field_target_delta',
    'field_target_file',
    'field_proposed_alt',
    'field_review_status',
    'field_source_framework',
    'field_run_id',
    'field_evidence_hash',
  ] as $field_name) {
    if (!isset($fields[$field_name])) {
      step12_fail(sprintf('Missing %s.%s. Complete Step 8 first.', STEP12_BUNDLE, $field_name));
    }
  }

  $allowed_sources = $fields['field_source_framework']->getSetting('allowed_values');
  if (!isset($allowed_sources['phase0_fixture'])) {
    step12_fail('field_source_framework does not allow phase0_fixture. Install and migrate Step 8 v3.1.0 first.');
  }

  $editor = step12_load_user('editor_dana');
  $agent = step12_load_user('agent_bot');
  step12_assert_role_permission($editor, 'edit any alt_text_suggestion content');
  step12_assert_role_permission($editor, 'view alt_text_suggestion revisions');
  step12_assert_role_permission($agent, 'create alt_text_suggestion content');

  foreach (step12_case_definitions() as $definition) {
    $article = step12_load_article((string) $definition['article_title']);
    $delta = (int) $definition['delta'];
    $item = $article->get('field_image')->get($delta);
    if ($item === NULL || $item->target_id === NULL) {
      step12_fail(sprintf(
        'Target Article %02d does not have field_image delta %d.',
        (int) $definition['article_number'],
        $delta,
      ));
    }
  }
}

/**
 * Performs non-mutating environment checks.
 */
function step12_preflight(): void {
  $suggestion_count = step12_count_all_suggestions();
  if ($suggestion_count !== 0) {
    step12_fail(sprintf(
      'Step 12 preflight requires seeded-clean with zero suggestions; found %d. Run Step 10 reset.',
      $suggestion_count,
    ));
  }

  step12_ok('Preflight passed: revisioned suggestion bundle, reviewer permissions, accounts, and three target usages are ready.');
}

/**
 * Creates exactly three pending suggestions as agent_bot.
 */
function step12_prepare(): void {
  step12_preflight();

  $agent = step12_load_user('agent_bot');
  $account_switcher = \Drupal::service('account_switcher');
  $created = [];
  $base_time = \Drupal::time()->getRequestTime() - 180;

  $account_switcher->switchTo($agent);
  try {
    foreach (step12_case_definitions() as $index => $definition) {
      $article = step12_load_article((string) $definition['article_title']);
      $delta = (int) $definition['delta'];
      $image_item = $article->get('field_image')->get($delta);
      if ($image_item === NULL || $image_item->target_id === NULL) {
        step12_fail(sprintf('Missing target item for case %s.', $definition['case_id']));
      }

      $evidence_context = [
        'step' => 12,
        'case_id' => $definition['case_id'],
        'article_uuid' => $article->uuid(),
        'article_revision' => (int) $article->getRevisionId(),
        'field' => 'field_image',
        'delta' => $delta,
        'file_id' => (int) $image_item->target_id,
        'source_origin' => $definition['source_origin'],
      ];

      $suggestion = Node::create([
        'type' => STEP12_BUNDLE,
        'uuid' => step12_uuid_v5(STEP12_NAMESPACE_UUID, 'case:' . $definition['case_id']),
        'title' => $definition['title'],
        'uid' => (int) $agent->id(),
        'status' => 1,
        'field_target_node' => ['target_id' => (int) $article->id()],
        'field_target_revision' => ['value' => (int) $article->getRevisionId()],
        'field_target_field' => ['value' => 'field_image'],
        'field_target_delta' => ['value' => $delta],
        'field_target_file' => ['target_id' => (int) $image_item->target_id],
        'field_proposed_alt' => ['value' => $definition['initial_alt']],
        'field_review_status' => ['value' => 'pending'],
        'field_source_framework' => ['value' => $definition['source_origin']],
        'field_run_id' => ['value' => STEP12_RUN_ID],
        'field_evidence_hash' => ['value' => hash('sha256', json_encode($evidence_context, JSON_THROW_ON_ERROR))],
      ]);
      $suggestion->setNewRevision(TRUE);
      $suggestion->setRevisionUserId((int) $agent->id());
      $suggestion->setRevisionCreationTime($base_time + ($index * 60));
      $suggestion->setRevisionLogMessage(sprintf(
        'Step 12 case %s created by agent_bot for pending human review.',
        $definition['case_id'],
      ));
      $suggestion->save();
      $created[] = sprintf('%s=node:%d', $definition['case_id'], (int) $suggestion->id());
    }
  }
  finally {
    $account_switcher->switchBack();
  }

  step12_ok('Created three pending reviewer fixtures: ' . implode(', ', $created) . '.');
  step12_note('Complete the three review actions through Drupal as editor_dana, then run Step 12 audit.');
}

/**
 * Audits either the initial pending state or completed reviewer state.
 */
function step12_audit(string $expected_state, bool $verbose): array {
  $evidence = step12_collect_evidence();
  $errors = [];

  if ((int) $evidence['suggestion_count'] !== 3) {
    $errors[] = sprintf('Expected exactly three suggestions; found %d.', $evidence['suggestion_count']);
  }

  foreach ($evidence['cases'] as $case) {
    $first = $case['revisions'][0] ?? NULL;
    $latest = $case['revisions'][count($case['revisions']) - 1] ?? NULL;
    if (!is_array($first) || !is_array($latest)) {
      $errors[] = sprintf('Case %s has no inspectable revisions.', $case['case_id']);
      continue;
    }

    if ($case['owner']['name'] !== 'agent_bot') {
      $errors[] = sprintf('Case %s node owner is %s, expected agent_bot.', $case['case_id'], $case['owner']['name']);
    }
    if ($first['revision_user']['name'] !== 'agent_bot') {
      $errors[] = sprintf('Case %s initial revision user is %s, expected agent_bot.', $case['case_id'], $first['revision_user']['name']);
    }
    if ($first['review_status'] !== 'pending') {
      $errors[] = sprintf('Case %s initial status is %s, expected pending.', $case['case_id'], $first['review_status']);
    }
    if ($first['proposed_alt'] !== $case['expected']['initial_alt']) {
      $errors[] = sprintf('Case %s initial proposed alt does not match the fixture.', $case['case_id']);
    }
    if ($first['source_framework'] !== $case['source_framework']) {
      $errors[] = sprintf('Case %s initial source origin changed.', $case['case_id']);
    }
    if ((int) $first['target_revision'] !== (int) $case['target']['content_revision']) {
      $errors[] = sprintf('Case %s target content revision changed.', $case['case_id']);
    }

    if ($expected_state === 'pending') {
      if ((int) $case['revision_count'] !== 1) {
        $errors[] = sprintf('Case %s should have exactly one pending revision; found %d.', $case['case_id'], $case['revision_count']);
      }
      if ($latest['review_status'] !== 'pending') {
        $errors[] = sprintf('Case %s is no longer pending before reviewer action.', $case['case_id']);
      }
      continue;
    }

    if ((int) $case['revision_count'] < 2) {
      $errors[] = sprintf('Case %s has %d revision(s); expected at least two after review.', $case['case_id'], $case['revision_count']);
    }
    if ($latest['revision_user']['name'] !== 'editor_dana') {
      $errors[] = sprintf('Case %s latest revision user is %s, expected editor_dana.', $case['case_id'], $latest['revision_user']['name']);
    }
    if ($latest['review_status'] !== $case['expected']['status']) {
      $errors[] = sprintf(
        'Case %s latest status is %s, expected %s.',
        $case['case_id'],
        $latest['review_status'],
        $case['expected']['status'],
      );
    }
    if ($latest['proposed_alt'] !== $case['expected']['alt']) {
      $errors[] = sprintf('Case %s latest proposed alt does not match the expected reviewer result.', $case['case_id']);
    }
    if ($latest['source_framework'] !== $first['source_framework']) {
      $errors[] = sprintf('Case %s source origin changed during review.', $case['case_id']);
    }
    if ((int) $latest['target_revision'] !== (int) $first['target_revision']) {
      $errors[] = sprintf('Case %s target content revision changed during review.', $case['case_id']);
    }
    if ((int) $latest['timestamp_unix'] < (int) $first['timestamp_unix']) {
      $errors[] = sprintf('Case %s reviewer timestamp precedes its initial revision.', $case['case_id']);
    }

    if ($case['case_id'] === 'C' && $latest['proposed_alt'] === $first['proposed_alt']) {
      $errors[] = 'Case C does not show an editorial text change.';
    }
    if ($case['case_id'] !== 'C' && $latest['proposed_alt'] !== $first['proposed_alt']) {
      $errors[] = sprintf('Case %s proposed alt changed but should have remained unchanged.', $case['case_id']);
    }
  }

  if ($errors !== []) {
    foreach ($errors as $error) {
      step12_error($error);
    }
    step12_fail(sprintf('Step 12 %s audit failed with %d issue(s).', $expected_state, count($errors)));
  }

  if ($verbose) {
    foreach ($evidence['cases'] as $case) {
      $latest = $case['revisions'][count($case['revisions']) - 1];
      step12_note(sprintf(
        'Case %s: %d revision(s) · %s → %s · latest reviewer %s · origin %s · target revision %d.',
        $case['case_id'],
        $case['revision_count'],
        $case['revisions'][0]['review_status'],
        $latest['review_status'],
        $latest['revision_user']['name'],
        $case['source_framework'],
        $case['target']['content_revision'],
      ));
    }
    step12_ok(sprintf('Step 12 %s audit passed.', $expected_state));
  }

  return $evidence;
}

/**
 * Emits validated evidence as JSON without informational prose.
 */
function step12_emit_json(string $expected_state): void {
  $evidence = step12_audit($expected_state, FALSE);
  $evidence['audit_state'] = $expected_state;
  $evidence['generated_at'] = gmdate('c');
  fwrite(STDOUT, json_encode(
    $evidence,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
  ) . PHP_EOL);
}

/**
 * Collects current and historical values for all three Step 12 cases.
 */
function step12_collect_evidence(): array {
  $node_storage = \Drupal::entityTypeManager()->getStorage('node');
  if (!$node_storage instanceof RevisionableStorageInterface) {
    step12_fail('Node storage does not support revisions.');
  }

  $cases = [];
  foreach (step12_case_definitions() as $definition) {
    $ids = $node_storage->getQuery()
      ->accessCheck(FALSE)
      ->condition('type', STEP12_BUNDLE)
      ->condition('field_run_id', STEP12_RUN_ID)
      ->condition('title', $definition['title'])
      ->execute();

    if (count($ids) !== 1) {
      step12_fail(sprintf(
        'Expected exactly one suggestion titled "%s"; found %d.',
        $definition['title'],
        count($ids),
      ));
    }

    $node = $node_storage->load((int) reset($ids));
    if (!$node instanceof NodeInterface) {
      step12_fail(sprintf('Unable to load case %s suggestion.', $definition['case_id']));
    }

    $revision_ids = \Drupal::database()->select('node_revision', 'nr')
      ->fields('nr', ['vid'])
      ->condition('nid', (int) $node->id())
      ->orderBy('vid', 'ASC')
      ->execute()
      ->fetchCol();

    $revisions = [];
    foreach ($revision_ids as $revision_id) {
      $revision = $node_storage->loadRevision((int) $revision_id);
      if (!$revision instanceof NodeInterface) {
        step12_fail(sprintf('Unable to load revision %d for case %s.', $revision_id, $definition['case_id']));
      }
      $revision_user = step12_load_user_by_id((int) $revision->getRevisionUserId());
      $revisions[] = [
        'revision_id' => (int) $revision->getRevisionId(),
        'revision_user' => [
          'uid' => (int) $revision_user->id(),
          'name' => $revision_user->getAccountName(),
        ],
        'timestamp_unix' => (int) $revision->getRevisionCreationTime(),
        'timestamp_utc' => gmdate('c', (int) $revision->getRevisionCreationTime()),
        'revision_log' => (string) ($revision->getRevisionLogMessage() ?? ''),
        'proposed_alt' => (string) $revision->get('field_proposed_alt')->value,
        'review_status' => (string) $revision->get('field_review_status')->value,
        'source_framework' => (string) $revision->get('field_source_framework')->value,
        'run_id' => (string) $revision->get('field_run_id')->value,
        'target_revision' => (int) $revision->get('field_target_revision')->value,
      ];
    }

    $owner = step12_load_user_by_id((int) $node->getOwnerId());
    $target_node = $node->get('field_target_node')->entity;
    $target_file = $node->get('field_target_file')->entity;
    if (!$target_node instanceof NodeInterface || $target_file === NULL) {
      step12_fail(sprintf('Case %s target references are incomplete.', $definition['case_id']));
    }

    $cases[] = [
      'case_id' => $definition['case_id'],
      'title' => $definition['title'],
      'action' => $definition['action'],
      'review_instruction' => $definition['review_instruction'],
      'node_id' => (int) $node->id(),
      'node_uuid' => $node->uuid(),
      'owner' => [
        'uid' => (int) $owner->id(),
        'name' => $owner->getAccountName(),
      ],
      'source_framework' => $definition['source_origin'],
      'target' => [
        'article_number' => (int) $definition['article_number'],
        'node_id' => (int) $target_node->id(),
        'node_uuid' => $target_node->uuid(),
        'node_title' => $target_node->label(),
        'content_revision' => (int) $node->get('field_target_revision')->value,
        'field_name' => (string) $node->get('field_target_field')->value,
        'delta' => (int) $node->get('field_target_delta')->value,
        'file_id' => (int) $target_file->id(),
        'file_uuid' => $target_file->uuid(),
      ],
      'expected' => [
        'initial_alt' => $definition['initial_alt'],
        'status' => $definition['expected_status'],
        'alt' => $definition['expected_alt'],
      ],
      'revision_count' => count($revisions),
      'revisions' => $revisions,
      'paths' => [
        'view' => '/node/' . $node->id(),
        'edit' => '/node/' . $node->id() . '/edit',
        'history' => '/node/' . $node->id() . '/revisions',
        'initial_revision' => '/node/' . $node->id() . '/revisions/' . ($revision_ids[0] ?? '') . '/view',
      ],
    ];
  }

  return [
    'schema_version' => 1,
    'step12_helper_version' => STEP12_HELPER_VERSION,
    'fixture_run_id' => STEP12_RUN_ID,
    'suggestion_count' => step12_count_all_suggestions(),
    'cases' => $cases,
  ];
}

/**
 * Loads a required deterministic Article by title.
 */
function step12_load_article(string $title): NodeInterface {
  $storage = \Drupal::entityTypeManager()->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->condition('title', $title)
    ->execute();

  if (count($ids) !== 1) {
    step12_fail(sprintf('Expected exactly one Article titled "%s"; found %d.', $title, count($ids)));
  }

  $node = $storage->load((int) reset($ids));
  if (!$node instanceof NodeInterface) {
    step12_fail('Unable to load target Article: ' . $title);
  }
  return $node;
}

/**
 * Counts every suggestion node. The Step 10 baseline should contain none.
 */
function step12_count_all_suggestions(): int {
  return (int) \Drupal::entityTypeManager()->getStorage('node')->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP12_BUNDLE)
    ->count()
    ->execute();
}

/**
 * Loads a required active user by account name.
 */
function step12_load_user(string $username): UserInterface {
  $storage = \Drupal::entityTypeManager()->getStorage('user');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('name', $username)
    ->execute();

  if (count($ids) !== 1) {
    step12_fail(sprintf('Expected exactly one user named %s; found %d.', $username, count($ids)));
  }
  return step12_load_user_by_id((int) reset($ids));
}

/**
 * Loads an active user by ID.
 */
function step12_load_user_by_id(int $uid): UserInterface {
  $user = \Drupal::entityTypeManager()->getStorage('user')->load($uid);
  if (!$user instanceof UserInterface || !$user->isActive()) {
    step12_fail(sprintf('Required active user ID %d is unavailable.', $uid));
  }
  return $user;
}

/**
 * Verifies the user has a permission through one of their assigned roles.
 */
function step12_assert_role_permission(UserInterface $user, string $permission): void {
  $role_storage = \Drupal::entityTypeManager()->getStorage('user_role');
  $has_permission = FALSE;
  foreach ($user->getRoles(TRUE) as $role_id) {
    $role = $role_storage->load($role_id);
    if ($role instanceof RoleInterface && $role->hasPermission($permission)) {
      $has_permission = TRUE;
      break;
    }
  }
  if (!$has_permission) {
    step12_fail(sprintf('%s lacks required permission: %s', $user->getAccountName(), $permission));
  }
}

/**
 * Produces a stable RFC 4122 version-5 UUID.
 */
function step12_uuid_v5(string $namespace, string $name): string {
  $namespace_hex = str_replace(['-', '{', '}'], '', $namespace);
  if (strlen($namespace_hex) !== 32 || !ctype_xdigit($namespace_hex)) {
    step12_fail('Invalid Step 12 namespace UUID.');
  }
  $namespace_bytes = hex2bin($namespace_hex);
  if ($namespace_bytes === FALSE) {
    step12_fail('Unable to decode Step 12 namespace UUID.');
  }
  $hash = sha1($namespace_bytes . $name);
  return sprintf(
    '%08s-%04s-%04x-%04x-%012s',
    substr($hash, 0, 8),
    substr($hash, 8, 4),
    (hexdec(substr($hash, 12, 4)) & 0x0fff) | 0x5000,
    (hexdec(substr($hash, 16, 4)) & 0x3fff) | 0x8000,
    substr($hash, 20, 12),
  );
}

function step12_note(string $message): void {
  fwrite(STDOUT, '[INFO] ' . $message . PHP_EOL);
}

function step12_ok(string $message): void {
  fwrite(STDOUT, '[OK] ' . $message . PHP_EOL);
}

function step12_error(string $message): void {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
}

function step12_fail(string $message): never {
  throw new RuntimeException($message);
}
