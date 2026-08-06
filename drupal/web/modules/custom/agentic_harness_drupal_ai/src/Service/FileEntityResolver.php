<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_drupal_ai\Service;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\File\FileSystemInterface;
use Drupal\file\FileInterface;

/**
 * Resolves one authorized File entity for AI Agents image transport.
 *
 * The URI is treated only as an entity-owned local transport locator. It is
 * never accepted from caller/model input and is never returned by this service.
 */
final class FileEntityResolver {

  private const APPROVED_SCHEMES = ['public', 'private'];

  private const CONTEXT_KEYS = [
    'schema_version',
    'target',
    'article',
    'image',
    'existing_alt',
    'evidence_hash',
    'collected_at',
  ];

  private const IMAGE_KEYS = [
    'file_uuid',
    'filename',
    'mime_type',
    'width',
    'height',
    'byte_length',
    'sha256',
    'representation',
  ];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly FileSystemInterface $fileSystem,
  ) {}

  /**
   * Resolves and re-verifies one File entity from authorized image context.
   *
   * @param array<string, mixed> $authorizedContext
   *   The direct data object returned by the permission-checked
   *   get_image_context adapter.
   *
   * @throws \RuntimeException
   *   When shape, identity, local transport, or current bytes differ.
   */
  public function resolve(array $authorizedContext): FileInterface {
    $this->assertExactKeys($authorizedContext, self::CONTEXT_KEYS, 'Authorized image context shape differs.');

    $image = $authorizedContext['image'] ?? NULL;
    if (!is_array($image) || array_is_list($image)) {
      throw new \RuntimeException('Authorized image context is unavailable.');
    }
    $this->assertExactKeys($image, self::IMAGE_KEYS, 'Authorized image identity shape differs.');

    foreach (['uri', 'path', 'resolved_path', 'file_id', 'target_id'] as $prohibited) {
      if (array_key_exists($prohibited, $authorizedContext) || array_key_exists($prohibited, $image)) {
        throw new \RuntimeException('Caller-supplied File locator or selector is prohibited.');
      }
    }

    $uuid = $image['file_uuid'];
    if (!is_string($uuid) || preg_match(
      '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i',
      $uuid,
    ) !== 1) {
      throw new \RuntimeException('Authorized File UUID is invalid.');
    }
    if (!is_string($image['filename']) || $image['filename'] === '') {
      throw new \RuntimeException('Authorized filename is invalid.');
    }
    if (!is_string($image['mime_type']) || !str_starts_with($image['mime_type'], 'image/')) {
      throw new \RuntimeException('Authorized MIME type is invalid.');
    }
    if (!is_int($image['byte_length']) || $image['byte_length'] < 1) {
      throw new \RuntimeException('Authorized byte length is invalid.');
    }
    if (!is_string($image['sha256']) || preg_match('/^[a-f0-9]{64}$/', $image['sha256']) !== 1) {
      throw new \RuntimeException('Authorized image hash is invalid.');
    }

    $matches = $this->entityTypeManager
      ->getStorage('file')
      ->loadByProperties(['uuid' => $uuid]);
    if (count($matches) !== 1) {
      throw new \RuntimeException('Authorized File UUID did not resolve to exactly one entity.');
    }

    $file = reset($matches);
    if (!$file instanceof FileInterface) {
      throw new \RuntimeException('Authorized File UUID did not resolve to FileInterface.');
    }

    if (
      $file->uuid() !== $uuid
      || $file->getFilename() !== $image['filename']
      || $file->getMimeType() !== $image['mime_type']
    ) {
      throw new \RuntimeException('Resolved File entity identity differs from authorized context.');
    }

    $uri = $file->getFileUri();
    if (!is_string($uri) || $uri === '') {
      throw new \RuntimeException('Resolved File entity has no local transport locator.');
    }
    $scheme = parse_url($uri, PHP_URL_SCHEME);
    if (!is_string($scheme) || !in_array($scheme, self::APPROVED_SCHEMES, TRUE)) {
      throw new \RuntimeException('Resolved File entity uses an unapproved stream-wrapper scheme.');
    }
    if (preg_match('/^https?:\/\//i', $uri) === 1) {
      throw new \RuntimeException('Remote File transport is prohibited.');
    }

    $realpath = $this->fileSystem->realpath($uri);
    if ($realpath === FALSE || !is_readable($realpath) || !is_file($realpath)) {
      throw new \RuntimeException('Resolved File entity does not map to a readable local file.');
    }

    $bytes = file_get_contents($realpath);
    if ($bytes === FALSE || $bytes === '') {
      throw new \RuntimeException('Resolved File bytes are unavailable.');
    }
    if (strlen($bytes) !== $image['byte_length']) {
      throw new \RuntimeException('Resolved File byte length differs from authorized context.');
    }
    if (!hash_equals($image['sha256'], hash('sha256', $bytes))) {
      throw new \RuntimeException('Resolved File hash differs from authorized context.');
    }

    return $file;
  }

  /**
   * @param array<string, mixed> $value
   * @param array<int, string> $expected
   */
  private function assertExactKeys(array $value, array $expected, string $message): void {
    $actual = array_keys($value);
    sort($actual);
    sort($expected);
    if ($actual !== $expected) {
      throw new \RuntimeException($message);
    }
  }

}
