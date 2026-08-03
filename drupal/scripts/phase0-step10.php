<?php

declare(strict_types=1);

/**
 * Phase 0, Step 10: Drupal-side snapshot/reset assertions.
 *
 * This companion is invoked by run-phase0-step10.sh after Drupal is fully
 * bootstrapped by Drush. DDEV snapshot/export/archive orchestration remains in
 * the Bash runner because those are host-side operations.
 *
 * Commands:
 *   ddev drush php:script scripts/phase0-step10.php -- audit-clean
 *   ddev drush php:script scripts/phase0-step10.php -- mutate-test
 *   ddev drush php:script scripts/phase0-step10.php -- assert-mutated
 */

use Drupal\node\Entity\Node;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

const STEP10_HELPER_VERSION = '1.0.3';
const STEP10_ARTICLE_TITLE = 'Phase 0 01 — Emergency Preparedness Checklist';
const STEP10_SUGGESTION_BUNDLE = 'alt_text_suggestion';
const STEP10_IMAGE_FIELD = 'field_image';
const STEP10_TEST_ALT = 'TEMPORARY STEP 10 RESET MUTATION — MUST DISAPPEAR';
const STEP10_TEST_RUN_ID = 'phase0-step10-reset-test';
const STEP10_TEST_SUGGESTION_TITLE = 'STEP 10 RESET TEST — MUST DISAPPEAR';
const STEP10_TEST_SOURCE = 'phase0_fixture';

$args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $args[0] ?? 'audit-clean';

if (!in_array($mode, ['audit-clean', 'mutate-test', 'assert-mutated'], TRUE)) {
  step10_fail(sprintf(
    'Unknown mode "%s". Use: audit-clean, mutate-test, or assert-mutated.',
    $mode,
  ));
}

step10_note('Step 10 helper version: ' . STEP10_HELPER_VERSION);
step10_require_environment();

switch ($mode) {
  case 'audit-clean':
    step10_audit_clean();
    break;

  case 'mutate-test':
    step10_mutate_test();
    break;

  case 'assert-mutated':
    step10_assert_mutated();
    break;
}

/**
 * Verifies the exact Drupal-side conditions required for a clean baseline.
 */
function step10_audit_clean(): void {
  $article = step10_load_seed_article();
  $alt = step10_get_primary_alt($article);

  if ($alt !== '') {
    step10_fail(sprintf(
      'Seed Article 01 delta 0 is not clean. Expected empty alt text; found "%s".',
      $alt,
    ));
  }

  $suggestion_count = step10_count_all_suggestions();
  if ($suggestion_count !== 0) {
    step10_fail(sprintf(
      'Clean baseline requires zero Alt text suggestion nodes; found %d.',
      $suggestion_count,
    ));
  }

  $test_suggestion_count = step10_count_test_suggestions();
  if ($test_suggestion_count !== 0) {
    step10_fail(sprintf(
      'The temporary Step 10 suggestion still exists; found %d matching records.',
      $test_suggestion_count,
    ));
  }

  step10_ok(sprintf(
    'Drupal baseline is clean: Article 01 alt is empty and suggestion count is %d.',
    $suggestion_count,
  ));
}

/**
 * Creates a controlled drift condition for the reset proof.
 */
function step10_mutate_test(): void {
  step10_audit_clean();

  $article = step10_load_seed_article();
  $items = $article->get(STEP10_IMAGE_FIELD)->getValue();
  if (!isset($items[0]['target_id'])) {
    step10_fail('Seed Article 01 does not have field_image delta 0.');
  }

  $items[0]['alt'] = STEP10_TEST_ALT;
  $article->set(STEP10_IMAGE_FIELD, $items);
  $article->setNewRevision(TRUE);
  $article->setRevisionCreationTime(\Drupal::time()->getRequestTime());

  $editor = step10_load_user('editor_dana');
  if (method_exists($article, 'setRevisionUserId')) {
    $article->setRevisionUserId((int) $editor->id());
  }
  if (method_exists($article, 'setRevisionLogMessage')) {
    $article->setRevisionLogMessage('Temporary Step 10 reset verification mutation.');
  }
  $article->save();

  $agent = step10_load_user('agent_bot');
  $file_id = (int) $items[0]['target_id'];

  $suggestion = Node::create([
    'type' => STEP10_SUGGESTION_BUNDLE,
    'title' => STEP10_TEST_SUGGESTION_TITLE,
    'uid' => (int) $agent->id(),
    'status' => 1,
    'field_target_node' => ['target_id' => (int) $article->id()],
    'field_target_revision' => ['value' => (int) $article->getRevisionId()],
    'field_target_field' => ['value' => STEP10_IMAGE_FIELD],
    'field_target_delta' => ['value' => 0],
    'field_target_file' => ['target_id' => $file_id],
    'field_proposed_alt' => ['value' => 'Temporary recommendation created only to prove snapshot reset.'],
    'field_review_status' => ['value' => 'pending'],
    'field_source_framework' => ['value' => STEP10_TEST_SOURCE],
    'field_run_id' => ['value' => STEP10_TEST_RUN_ID],
    'field_evidence_hash' => ['value' => hash('sha256', STEP10_TEST_ALT)],
  ]);
  $suggestion->setNewRevision(TRUE);
  $suggestion->save();

  step10_ok(sprintf(
    'Created controlled drift: Article 01 revision %d now has the temporary alt value and suggestion node %d exists.',
    (int) $article->getRevisionId(),
    (int) $suggestion->id(),
  ));
}

/**
 * Confirms that the controlled drift exists before reset is attempted.
 */
function step10_assert_mutated(): void {
  $article = step10_load_seed_article();
  $alt = step10_get_primary_alt($article);
  if ($alt !== STEP10_TEST_ALT) {
    step10_fail(sprintf(
      'Expected the temporary Article alt mutation, but found "%s".',
      $alt,
    ));
  }

  $test_count = step10_count_test_suggestions();
  if ($test_count !== 1) {
    step10_fail(sprintf(
      'Expected exactly one temporary Step 10 suggestion; found %d.',
      $test_count,
    ));
  }

  if (step10_count_all_suggestions() !== 1) {
    step10_fail('The reset test expected the temporary suggestion to be the only suggestion node.');
  }

  $test_suggestion = step10_load_test_suggestion();
  $source = (string) $test_suggestion->get('field_source_framework')->value;
  if ($source !== STEP10_TEST_SOURCE) {
    step10_fail(sprintf(
      'Temporary Step 10 suggestion has source %s; expected %s.',
      $source,
      STEP10_TEST_SOURCE,
    ));
  }

  step10_ok('Controlled drift is present and uses the neutral Phase 0 test-fixture origin.');
}

/**
 * Ensures required bundles, fields, and accounts exist.
 */
function step10_require_environment(): void {
  $node_type_storage = \Drupal::entityTypeManager()->getStorage('node_type');
  if ($node_type_storage->load('article') === NULL) {
    step10_fail('Missing Article content type. Complete Step 8 first.');
  }
  if ($node_type_storage->load(STEP10_SUGGESTION_BUNDLE) === NULL) {
    step10_fail('Missing alt_text_suggestion content type. Complete Step 8 first.');
  }

  $field_manager = \Drupal::service('entity_field.manager');
  $article_fields = $field_manager->getFieldDefinitions('node', 'article');
  if (!isset($article_fields[STEP10_IMAGE_FIELD])) {
    step10_fail('Missing article.field_image. Complete Step 8 first.');
  }

  $suggestion_fields = $field_manager->getFieldDefinitions('node', STEP10_SUGGESTION_BUNDLE);
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
    if (!isset($suggestion_fields[$field_name])) {
      step10_fail(sprintf('Missing %s.%s. Complete Step 8 first.', STEP10_SUGGESTION_BUNDLE, $field_name));
    }
  }

  $allowed_sources = $suggestion_fields['field_source_framework']->getSetting('allowed_values');
  if (!isset($allowed_sources[STEP10_TEST_SOURCE])) {
    step10_fail('field_source_framework does not allow phase0_fixture. Install and migrate Step 8 v3.1.0 first.');
  }

  step10_load_user('editor_dana');
  step10_load_user('agent_bot');
}

/**
 * Loads the deterministic first seed Article.
 */
function step10_load_seed_article(): NodeInterface {
  $storage = \Drupal::entityTypeManager()->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->condition('title', STEP10_ARTICLE_TITLE)
    ->execute();

  if (count($ids) !== 1) {
    step10_fail(sprintf(
      'Expected exactly one seed Article titled "%s"; found %d.',
      STEP10_ARTICLE_TITLE,
      count($ids),
    ));
  }

  $article = $storage->load((int) reset($ids));
  if (!$article instanceof NodeInterface) {
    step10_fail('Unable to load deterministic seed Article 01.');
  }

  return $article;
}

/**
 * Returns Article 01 field_image delta 0 alt text.
 */
function step10_get_primary_alt(NodeInterface $article): string {
  if ($article->get(STEP10_IMAGE_FIELD)->isEmpty()) {
    step10_fail('Seed Article 01 field_image is empty.');
  }

  $item = $article->get(STEP10_IMAGE_FIELD)->get(0);
  if ($item === NULL) {
    step10_fail('Seed Article 01 field_image delta 0 is missing.');
  }

  return (string) ($item->getValue()['alt'] ?? '');
}

/**
 * Loads a required active user by username.
 */
function step10_load_user(string $username): UserInterface {
  $storage = \Drupal::entityTypeManager()->getStorage('user');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('name', $username)
    ->execute();

  if (count($ids) !== 1) {
    step10_fail(sprintf('Expected exactly one user named %s; found %d.', $username, count($ids)));
  }

  $user = $storage->load((int) reset($ids));
  if (!$user instanceof UserInterface || !$user->isActive()) {
    step10_fail(sprintf('Required user %s is missing or inactive.', $username));
  }

  return $user;
}

/**
 * Counts all suggestion nodes in the clean lab database.
 */
function step10_count_all_suggestions(): int {
  return (int) \Drupal::entityTypeManager()->getStorage('node')->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP10_SUGGESTION_BUNDLE)
    ->count()
    ->execute();
}

/**
 * Loads the unique temporary reset-test suggestion.
 */
function step10_load_test_suggestion(): NodeInterface {
  $storage = \Drupal::entityTypeManager()->getStorage('node');
  $ids = $storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP10_SUGGESTION_BUNDLE)
    ->condition('field_run_id', STEP10_TEST_RUN_ID)
    ->execute();

  if (count($ids) !== 1) {
    step10_fail(sprintf('Expected exactly one temporary Step 10 suggestion; found %d.', count($ids)));
  }

  $suggestion = $storage->load((int) reset($ids));
  if (!$suggestion instanceof NodeInterface) {
    step10_fail('Unable to load the temporary Step 10 suggestion.');
  }
  return $suggestion;
}

/**
 * Counts reset-test suggestion nodes by stable run ID.
 */
function step10_count_test_suggestions(): int {
  return (int) \Drupal::entityTypeManager()->getStorage('node')->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', STEP10_SUGGESTION_BUNDLE)
    ->condition('field_run_id', STEP10_TEST_RUN_ID)
    ->count()
    ->execute();
}

function step10_note(string $message): void {
  fwrite(STDOUT, '[INFO] ' . $message . PHP_EOL);
}

function step10_ok(string $message): void {
  fwrite(STDOUT, '[OK] ' . $message . PHP_EOL);
}

function step10_fail(string $message): never {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
  exit(1);
}
