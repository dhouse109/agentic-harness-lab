<?php

declare(strict_types=1);

use Drupal\node\NodeInterface;
use Drupal\user\Entity\Role;

/**
 * Drush php:script helper for Phase 0 Step 17.
 *
 * Usage from drupal/:
 *   ddev drush --quiet php:script scripts/phase0-step17.php -- inspect
 *   ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot
 *   ddev drush --quiet php:script scripts/phase0-step17.php -- validate-identities /var/www/html/.phase0-step17-runtime/agent-response.json
 */

const STEP17_HELPER_VERSION = '1.0.0';

/** @var array<int, string> $extra */
$mode = $extra[0] ?? 'help';
$argument = $extra[1] ?? '';

/**
 * Emits stable JSON and returns control to Drush.
 */
function step17_emit(array $value): void {
  print json_encode($value, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . PHP_EOL;
}


/**
 * Loads a user account by name without relying on deprecated procedural APIs.
 */
function step17_load_user_by_name(string $name): ?\Drupal\user\UserInterface {
  $accounts = \Drupal::entityTypeManager()->getStorage('user')->loadByProperties(['name' => $name]);
  $account = reset($accounts);
  return $account instanceof \Drupal\user\UserInterface ? $account : NULL;
}

/**
 * Canonically sorts nested arrays for stable hashing.
 */
function step17_canonicalize(mixed $value): mixed {
  if (!is_array($value)) {
    return $value;
  }
  if (array_is_list($value)) {
    return array_map('step17_canonicalize', $value);
  }
  ksort($value);
  foreach ($value as $key => $item) {
    $value[$key] = step17_canonicalize($item);
  }
  return $value;
}

/**
 * Creates a source-content snapshot without retaining file bytes.
 */
function step17_snapshot(): array {
  $node_storage = \Drupal::entityTypeManager()->getStorage('node');
  $nids = $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->sort('nid', 'ASC')
    ->execute();

  $articles = [];
  foreach ($node_storage->loadMultiple($nids) as $node) {
    if (!$node instanceof NodeInterface) {
      continue;
    }
    $images = [];
    if ($node->hasField('field_image')) {
      foreach ($node->get('field_image') as $delta => $item) {
        $file = $item->entity;
        $images[] = [
          'delta' => (int) $delta,
          'file_uuid' => $file ? $file->uuid() : NULL,
          'alt' => isset($item->alt) ? (string) $item->alt : '',
          'title' => isset($item->title) ? (string) $item->title : '',
        ];
      }
    }
    $articles[] = [
      'node_uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'title' => (string) $node->label(),
      'status' => (bool) $node->isPublished(),
      'images' => $images,
    ];
  }

  $suggestion_count = (int) $node_storage->getQuery()
    ->accessCheck(FALSE)
    ->condition('type', 'alt_text_suggestion')
    ->count()
    ->execute();

  $canonical = step17_canonicalize([
    'articles' => $articles,
    'suggestion_count' => $suggestion_count,
  ]);
  $json = json_encode($canonical, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);

  return [
    'helper_version' => STEP17_HELPER_VERSION,
    'test_id' => 'S17-SNAPSHOT',
    'status' => 'pass',
    'article_count' => count($articles),
    'suggestion_count' => $suggestion_count,
    'source_sha256' => hash('sha256', $json),
  ];
}

/**
 * Verifies route, service, role, permission, and negative user scope.
 */
function step17_inspect(): array {
  $module_handler = \Drupal::moduleHandler();
  if (!$module_handler->moduleExists('agentic_harness_tools')) {
    throw new RuntimeException('agentic_harness_tools is not enabled.');
  }

  $route = \Drupal::service('router.route_provider')
    ->getRouteByName('agentic_harness_tools.find_images_needing_review');
  if ($route->getPath() !== '/api/agentic-harness/v1/images-needing-review') {
    throw new RuntimeException('Unexpected Step 17 route path.');
  }
  if ($route->getRequirement('_permission') !== 'use agentic harness discovery tools') {
    throw new RuntimeException('Unexpected Step 17 route permission.');
  }
  if ($route->getOption('_auth') !== ['basic_auth']) {
    throw new RuntimeException('Step 17 route is not restricted to Drupal core basic_auth.');
  }
  if ($route->getOption('no_cache') !== TRUE) {
    throw new RuntimeException('Step 17 route must remain uncacheable.');
  }

  $agent_role = Role::load('agent_service');
  if (!$agent_role || !$agent_role->hasPermission('use agentic harness discovery tools')) {
    throw new RuntimeException('agent_service does not have the discovery permission.');
  }

  $agent = step17_load_user_by_name('agent_bot');
  $editor = step17_load_user_by_name('editor_dana');
  if (!$agent || !$agent->hasPermission('use agentic harness discovery tools')) {
    throw new RuntimeException('agent_bot cannot use the discovery operation.');
  }
  if (!$editor) {
    throw new RuntimeException('editor_dana was not found.');
  }
  if ($editor->hasPermission('use agentic harness discovery tools')) {
    throw new RuntimeException('editor_dana unexpectedly has the service discovery permission.');
  }

  $finder = \Drupal::service('agentic_harness_tools.image_review_finder');
  if (!$finder instanceof \Drupal\agentic_harness_tools\Service\ImageReviewFinder) {
    throw new RuntimeException('ImageReviewFinder service did not resolve.');
  }

  return [
    'helper_version' => STEP17_HELPER_VERSION,
    'test_id' => 'S17-INSPECT-001',
    'status' => 'pass',
    'route_name' => 'agentic_harness_tools.find_images_needing_review',
    'route_path' => $route->getPath(),
    'permission' => 'use agentic harness discovery tools',
    'agent_role' => 'agent_service',
    'agent_username' => 'agent_bot',
    'editor_username' => 'editor_dana',
    'editor_permission_denied' => TRUE,
    'model_dependency' => FALSE,
  ];
}

/**
 * Validates every returned identity against current Drupal entities and access.
 */
function step17_validate_identities(string $path): array {
  if ($path === '' || !is_file($path)) {
    throw new RuntimeException('Response file was not found: ' . $path);
  }
  $decoded = json_decode((string) file_get_contents($path), TRUE, 512, JSON_THROW_ON_ERROR);
  $targets = $decoded['data']['targets'] ?? NULL;
  if (!is_array($targets)) {
    throw new RuntimeException('Response does not contain data.targets.');
  }

  $account = step17_load_user_by_name('agent_bot');
  if (!$account) {
    throw new RuntimeException('agent_bot was not found.');
  }
  $node_storage = \Drupal::entityTypeManager()->getStorage('node');
  $repository = \Drupal::service('entity.repository');
  $validated = [];

  foreach ($targets as $target) {
    $node = $repository->loadEntityByUuid('node', (string) ($target['node_uuid'] ?? ''));
    if (!$node instanceof NodeInterface) {
      throw new RuntimeException('Target node UUID does not resolve.');
    }
    $revision_id = (int) ($target['revision_id'] ?? 0);
    $revision = $node_storage->loadRevision($revision_id);
    if (!$revision instanceof NodeInterface || $revision->uuid() !== $node->uuid()) {
      throw new RuntimeException('Target revision does not resolve to the target node.');
    }
    if ((int) $node->getRevisionId() !== $revision_id) {
      throw new RuntimeException('Target revision is not the current node revision.');
    }
    if (!$node->access('view', $account)) {
      throw new RuntimeException('agent_bot cannot view target node ' . $node->uuid());
    }

    $field_name = (string) ($target['field_name'] ?? '');
    $delta = (int) ($target['delta'] ?? -1);
    if ($field_name !== 'field_image' || !$revision->hasField($field_name)) {
      throw new RuntimeException('Target field is invalid.');
    }
    $field = $revision->get($field_name);
    if (!$field->access('view', $account) || !$field->offsetExists($delta)) {
      throw new RuntimeException('Target field delta is unavailable or inaccessible.');
    }
    $item = $field->get($delta);
    $file = $item->entity;
    if (!$file || $file->uuid() !== (string) ($target['file_uuid'] ?? '')) {
      throw new RuntimeException('Target file UUID does not match the referenced file.');
    }
    if (!$file->access('view', $account)) {
      throw new RuntimeException('agent_bot cannot view the referenced file.');
    }

    $existing_alt = isset($item->alt) ? (string) $item->alt : '';
    if ($existing_alt !== (string) ($target['existing_alt'] ?? '')) {
      throw new RuntimeException('Target existing_alt does not match Drupal state.');
    }

    $validated[] = [
      'sequence' => (int) $target['sequence'],
      'node_uuid' => $node->uuid(),
      'revision_id' => $revision_id,
      'field_name' => $field_name,
      'delta' => $delta,
      'file_uuid' => $file->uuid(),
      'access_allowed' => TRUE,
    ];
  }

  return [
    'helper_version' => STEP17_HELPER_VERSION,
    'test_id' => 'S17-IDENTITY-001',
    'status' => 'pass',
    'validated_count' => count($validated),
    'account' => 'agent_bot',
    'targets' => $validated,
  ];
}

try {
  switch ($mode) {
    case 'inspect':
      step17_emit(step17_inspect());
      break;

    case 'snapshot':
      step17_emit(step17_snapshot());
      break;

    case 'validate-identities':
      step17_emit(step17_validate_identities($argument));
      break;

    case 'help':
    default:
      step17_emit([
        'helper_version' => STEP17_HELPER_VERSION,
        'status' => 'help',
        'modes' => ['inspect', 'snapshot', 'validate-identities'],
      ]);
      break;
  }
}
catch (Throwable $exception) {
  fwrite(STDERR, '[ERROR] ' . $exception->getMessage() . PHP_EOL);
  throw $exception;
}
