<?php

declare(strict_types=1);

/**
 * Phase 0, Step 7: create least-privilege Drupal roles and accounts.
 *
 * Run from the Drupal project root:
 *
 *   ddev drush php:script scripts/phase0-step7.php -- bootstrap
 *
 * After Step 8 creates the alt_text_suggestion content type:
 *
 *   ddev drush php:script scripts/phase0-step7.php -- finalize
 *
 * Audit without making changes:
 *
 *   ddev drush php:script scripts/phase0-step7.php -- audit
 *
 * To reset both generated passwords intentionally:
 *
 *   ddev drush php:script scripts/phase0-step7.php -- bootstrap reset-passwords
 *
 * Passwords are never printed. New/reset credentials are written to:
 *   <project-root>/.secrets/phase0-step7-accounts.txt
 */

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Entity\EntityStorageInterface;
use Drupal\user\RoleInterface;
use Drupal\user\UserInterface;

$script_args = array_values(array_filter($extra ?? [], 'is_string'));
$mode = $script_args[0] ?? 'bootstrap';
$reset_passwords = in_array('reset-passwords', $script_args, TRUE)
  || in_array('--reset-passwords', $script_args, TRUE);

$allowed_modes = ['bootstrap', 'finalize', 'audit'];
if (!in_array($mode, $allowed_modes, TRUE)) {
  fail(sprintf(
    'Unknown mode "%s". Use one of: %s.',
    $mode,
    implode(', ', $allowed_modes),
  ));
}

$entity_type_manager = \Drupal::entityTypeManager();
$role_storage = $entity_type_manager->getStorage('user_role');
$user_storage = $entity_type_manager->getStorage('user');
$node_type_storage = $entity_type_manager->getStorage('node_type');
$config_factory = \Drupal::configFactory();
$module_handler = \Drupal::moduleHandler();

if (!$module_handler->moduleExists('jsonapi')) {
  fail('The JSON:API module is not enabled. Run: ddev drush en jsonapi -y');
}

if (!$module_handler->moduleExists('basic_auth')) {
  warn('The Basic Auth module is not enabled. The accounts will be created, but later API credential tests will fail until it is enabled.');
}

if ($mode === 'finalize' && !$node_type_storage->load('alt_text_suggestion')) {
  fail('Cannot finalize: the alt_text_suggestion content type does not exist yet. Complete Step 8, then rerun in finalize mode.');
}

if ($mode === 'audit') {
  audit_state($role_storage, $user_storage, $config_factory);
  return;
}

$available_permissions = array_keys(
  \Drupal::service('user.permissions')->getPermissions(),
);

$content_editor_permissions = [
  'access content',
  'access administration pages',
  'access content overview',
  'access contextual links',
  'view the administration theme',
];

// Drupal 11 Standard commonly uses Navigation; older/minimal setups may use
// Toolbar. Add whichever permission actually exists.
foreach (['access navigation', 'access toolbar'] as $navigation_permission) {
  if (in_array($navigation_permission, $available_permissions, TRUE)) {
    $content_editor_permissions[] = $navigation_permission;
  }
}

$agent_service_permissions = [
  // Needed to read published Article content through JSON:API. This may also be
  // inherited from the authenticated role, but keeping it explicit documents
  // the service account's required read capability.
  'access content',
];

if ($mode === 'finalize') {
  $content_editor_permissions = array_merge($content_editor_permissions, [
    'edit any alt_text_suggestion content',
    'view alt_text_suggestion revisions',
  ]);

  $agent_service_permissions = array_merge($agent_service_permissions, [
    'create alt_text_suggestion content',
    // Allows the bot to inspect a suggestion it created if the POST leaves the
    // node unpublished. It does not permit editing, approval, or deletion.
    'view own unpublished content',
  ]);
}

$content_editor = ensure_role($role_storage, 'content_editor', 'Content editor');
$agent_service = ensure_role($role_storage, 'agent_service', 'Agent service');

sync_role_permissions(
  $content_editor,
  $content_editor_permissions,
  $available_permissions,
);
sync_role_permissions(
  $agent_service,
  $agent_service_permissions,
  $available_permissions,
);

$credentials = [];
$editor = ensure_user(
  $user_storage,
  username: 'editor_dana',
  email: 'editor_dana@example.test',
  required_role: 'content_editor',
  reset_password: $reset_passwords,
  generated_credentials: $credentials,
);
$agent = ensure_user(
  $user_storage,
  username: 'agent_bot',
  email: 'agent_bot@example.test',
  required_role: 'agent_service',
  reset_password: $reset_passwords,
  generated_credentials: $credentials,
);

$jsonapi_config = $config_factory->getEditable('jsonapi.settings');
if ($mode === 'bootstrap') {
  // Keep write routes disabled until the target bundle and its dynamic create
  // permission exist. This avoids a temporary, unnecessarily broad write mode.
  $jsonapi_config->set('read_only', TRUE)->save(TRUE);
  ok('JSON:API remains read-only until Step 8 is complete.');
}
else {
  // JSON:API's switch is global; Drupal entity access and bundle permissions
  // remain responsible for allowing/denying each actual operation.
  $jsonapi_config->set('read_only', FALSE)->save(TRUE);
  ok('JSON:API create/read/update/delete routes are enabled; role permissions remain the enforcement boundary.');
}

if ($credentials !== []) {
  $secret_path = write_credentials($credentials);
  ok(sprintf('New/reset account credentials were written to %s', $secret_path));
  note('The passwords were intentionally not printed to the terminal.');
}
else {
  note('Both accounts already existed, so their passwords were preserved. Add "reset-passwords" only when you intentionally want new credentials.');
}

ok(sprintf('Phase 0 Step 7 "%s" mode completed.', $mode));
audit_state($role_storage, $user_storage, $config_factory);

/**
 * Creates or loads a non-administrator role.
 */
function ensure_role(
  EntityStorageInterface $storage,
  string $id,
  string $label,
): RoleInterface {
  /** @var \Drupal\user\RoleInterface|null $role */
  $role = $storage->load($id);

  if ($role === NULL) {
    /** @var \Drupal\user\RoleInterface $role */
    $role = $storage->create([
      'id' => $id,
      'label' => $label,
      'is_admin' => FALSE,
    ]);
    $role->save();
    ok(sprintf('Created role: %s (%s)', $label, $id));
  }
  else {
    note(sprintf('Role already exists: %s (%s)', $role->label(), $id));
  }

  if ($role->isAdmin()) {
    $role->setIsAdmin(FALSE);
    $role->save();
    warn(sprintf('Removed administrator-role status from %s.', $id));
  }

  return $role;
}

/**
 * Replaces a role's permissions with an exact, validated allowlist.
 */
function sync_role_permissions(
  RoleInterface $role,
  array $desired_permissions,
  array $available_permissions,
): void {
  $desired_permissions = array_values(array_unique($desired_permissions));
  $missing_permissions = array_values(array_diff(
    $desired_permissions,
    $available_permissions,
  ));

  if ($missing_permissions !== []) {
    fail(sprintf(
      'Cannot configure role %s because these permissions do not exist: %s',
      $role->id(),
      implode(', ', $missing_permissions),
    ));
  }

  foreach ($role->getPermissions() as $permission) {
    $role->revokePermission($permission);
  }

  foreach ($desired_permissions as $permission) {
    $role->grantPermission($permission);
  }

  $role->setIsAdmin(FALSE);
  $role->save();
  ok(sprintf(
    'Synchronized %s to %d explicit permission(s).',
    $role->id(),
    count($desired_permissions),
  ));
}

/**
 * Creates or normalizes a user and ensures only one non-locked role remains.
 */
function ensure_user(
  EntityStorageInterface $storage,
  string $username,
  string $email,
  string $required_role,
  bool $reset_password,
  array &$generated_credentials,
): UserInterface {
  $matches = $storage->loadByProperties(['name' => $username]);
  /** @var \Drupal\user\UserInterface|null $user */
  $user = $matches === [] ? NULL : reset($matches);
  $created = FALSE;

  if ($user === NULL) {
    $password = generate_password();
    /** @var \Drupal\user\UserInterface $user */
    $user = $storage->create([
      'name' => $username,
      'mail' => $email,
      'status' => 1,
      'pass' => $password,
    ]);
    $created = TRUE;
    $generated_credentials[$username] = $password;
    ok(sprintf('Created account: %s', $username));
  }
  else {
    note(sprintf('Account already exists: %s', $username));
    $user->setEmail($email);
    $user->activate();
  }

  // Remove every optional role first. Authenticated is a locked, implicit role
  // and is not returned when TRUE is passed to getRoles().
  foreach ($user->getRoles(TRUE) as $role_id) {
    if ($role_id !== $required_role) {
      $user->removeRole($role_id);
      warn(sprintf('Removed unexpected role "%s" from %s.', $role_id, $username));
    }
  }

  if (!$user->hasRole($required_role)) {
    $user->addRole($required_role);
  }

  if (!$created && $reset_password) {
    $password = generate_password();
    $user->setPassword($password);
    $generated_credentials[$username] = $password;
    warn(sprintf('Reset password for %s by explicit request.', $username));
  }

  $user->save();
  ok(sprintf(
    'Normalized %s: active; optional role = %s.',
    $username,
    $required_role,
  ));

  return $user;
}

/**
 * Writes credentials outside webroot and adds the directory to .gitignore.
 */
function write_credentials(array $credentials): string {
  $project_root = dirname(DRUPAL_ROOT);
  $secret_directory = $project_root . '/.secrets';
  $secret_path = $secret_directory . '/phase0-step7-accounts.txt';
  $gitignore_path = $project_root . '/.gitignore';

  if (!is_dir($secret_directory)
    && !mkdir($secret_directory, 0700, TRUE)
    && !is_dir($secret_directory)) {
    fail(sprintf('Unable to create secret directory: %s', $secret_directory));
  }
  chmod($secret_directory, 0700);

  $lines = [
    '',
    '# Generated ' . gmdate('c'),
  ];
  foreach ($credentials as $username => $password) {
    $lines[] = sprintf('%s=%s', $username, $password);
  }

  $written = file_put_contents(
    $secret_path,
    implode(PHP_EOL, $lines) . PHP_EOL,
    FILE_APPEND | LOCK_EX,
  );
  if ($written === FALSE) {
    fail(sprintf('Unable to write credentials file: %s', $secret_path));
  }
  chmod($secret_path, 0600);

  $gitignore_entry = '.secrets/';
  $gitignore_contents = is_file($gitignore_path)
    ? (string) file_get_contents($gitignore_path)
    : '';
  $gitignore_lines = preg_split('/\R/', $gitignore_contents) ?: [];

  if (!in_array($gitignore_entry, $gitignore_lines, TRUE)) {
    $prefix = $gitignore_contents !== ''
      && !str_ends_with($gitignore_contents, PHP_EOL)
      ? PHP_EOL
      : '';
    file_put_contents(
      $gitignore_path,
      $prefix . $gitignore_entry . PHP_EOL,
      FILE_APPEND | LOCK_EX,
    );
  }

  return $secret_path;
}

function generate_password(): string {
  return rtrim(strtr(base64_encode(random_bytes(24)), '+/', '-_'), '=');
}

/**
 * Prints a compact security audit and exits nonzero on unsafe state.
 */
function audit_state(
  EntityStorageInterface $role_storage,
  EntityStorageInterface $user_storage,
  ConfigFactoryInterface $config_factory,
): void {
  line('');
  line('=== Phase 0 Step 7 audit ===');

  $expected_roles = [
    'content_editor' => 'editor_dana',
    'agent_service' => 'agent_bot',
  ];

  $unsafe = FALSE;

  foreach ($expected_roles as $role_id => $username) {
    /** @var \Drupal\user\RoleInterface|null $role */
    $role = $role_storage->load($role_id);
    if ($role === NULL) {
      error(sprintf('Missing role: %s', $role_id));
      $unsafe = TRUE;
      continue;
    }

    line(sprintf('Role %s permissions:', $role_id));
    foreach ($role->getPermissions() as $permission) {
      line('  - ' . $permission);
    }

    if ($role->isAdmin()) {
      error(sprintf('Role %s is incorrectly marked as an administrator role.', $role_id));
      $unsafe = TRUE;
    }

    $matches = $user_storage->loadByProperties(['name' => $username]);
    /** @var \Drupal\user\UserInterface|null $user */
    $user = $matches === [] ? NULL : reset($matches);
    if ($user === NULL) {
      error(sprintf('Missing user: %s', $username));
      $unsafe = TRUE;
      continue;
    }

    $optional_roles = array_values($user->getRoles(TRUE));
    line(sprintf(
      'User %s: status=%s; optional roles=%s',
      $username,
      $user->isActive() ? 'active' : 'blocked',
      $optional_roles === [] ? '(none)' : implode(', ', $optional_roles),
    ));

    if (!$user->isActive() || $optional_roles !== [$role_id]) {
      error(sprintf('%s does not have the expected single optional role.', $username));
      $unsafe = TRUE;
    }
  }

  $forbidden_agent_permissions = [
    'administer permissions',
    'administer users',
    'administer modules',
    'administer site configuration',
    'administer nodes',
    'administer content types',
    'bypass node access',
    'administer node published status',
    'create article content',
    'edit own article content',
    'edit any article content',
    'delete own article content',
    'delete any article content',
    'edit own alt_text_suggestion content',
    'edit any alt_text_suggestion content',
    'delete own alt_text_suggestion content',
    'delete any alt_text_suggestion content',
    'revert alt_text_suggestion revisions',
    'delete alt_text_suggestion revisions',
  ];

  /** @var \Drupal\user\RoleInterface|null $agent_role */
  $agent_role = $role_storage->load('agent_service');
  if ($agent_role !== NULL) {
    $bad = array_values(array_intersect(
      $forbidden_agent_permissions,
      $agent_role->getPermissions(),
    ));
    if ($bad !== []) {
      error('Agent service has forbidden permissions: ' . implode(', ', $bad));
      $unsafe = TRUE;
    }
    else {
      ok('Agent service has none of the explicitly forbidden permissions.');
    }
  }

  $read_only = (bool) $config_factory->get('jsonapi.settings')->get('read_only');
  line('JSON:API mode: ' . ($read_only ? 'read-only' : 'create/read/update/delete enabled'));

  if ($unsafe) {
    fail('Audit found one or more unsafe or incomplete conditions.');
  }

  ok('Audit passed.');
}

function line(string $message): void {
  fwrite(STDOUT, $message . PHP_EOL);
}

function ok(string $message): void {
  line('[OK] ' . $message);
}

function note(string $message): void {
  line('[INFO] ' . $message);
}

function warn(string $message): void {
  line('[WARN] ' . $message);
}

function error(string $message): void {
  fwrite(STDERR, '[ERROR] ' . $message . PHP_EOL);
}

function fail(string $message): never {
  error($message);
  exit(1);
}
