<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Service;

use Drupal\Component\Utility\Html;
use Drupal\agentic_harness_tools\Exception\ImageContextException;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\File\FileSystemInterface;
use Drupal\Core\Image\ImageFactory;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

/**
 * Returns permitted image and Article context for one exact frozen target.
 *
 * The operation is deterministic and model-free. It verifies the complete
 * field-usage identity before reading bytes and never mutates Drupal content.
 */
final class ImageContextProvider {

  private const TARGET_KEYS = [
    'schema_version',
    'sequence',
    'node_uuid',
    'revision_id',
    'field_name',
    'delta',
    'file_uuid',
    'target_state',
    'existing_alt',
  ];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly AccountProxyInterface $currentUser,
    private readonly FileSystemInterface $fileSystem,
    private readonly ImageFactory $imageFactory,
    private readonly ImageReviewFinder $finder,
  ) {}

  /**
   * @param array<string, mixed> $target
   *   One target conforming to target.schema.json.
   *
   * @return array<string, mixed>
   *   Context conforming to image-context.schema.json.
   */
  public function get(array $target): array {
    $this->validateTargetShape($target);
    $this->assertCurrentFrozenTarget($target);

    $node_storage = $this->entityTypeManager->getStorage('node');
    $matches = $node_storage->loadByProperties(['uuid' => $target['node_uuid']]);
    $node = reset($matches);
    if (!$node instanceof NodeInterface || !$node->access('view', $this->currentUser)) {
      throw new ImageContextException(
        'TARGET_UNAVAILABLE',
        'The target Article is unavailable to the calling account.',
        403,
      );
    }

    if ((int) $node->getRevisionId() !== $target['revision_id']) {
      throw $this->stale();
    }
    if (!$node->hasField($target['field_name'])) {
      throw $this->stale();
    }

    $field = $node->get($target['field_name']);
    if (!$field->access('view', $this->currentUser)) {
      throw new ImageContextException(
        'TARGET_UNAVAILABLE',
        'The target field is unavailable to the calling account.',
        403,
      );
    }
    $definition = $field->getFieldDefinition();
    if ($definition->getType() !== 'image' || !$field->offsetExists($target['delta'])) {
      throw $this->stale();
    }

    $item = $field->get($target['delta']);
    $file = $item?->entity;
    if (!$file instanceof FileInterface || !$file->access('view', $this->currentUser)) {
      throw new ImageContextException(
        'TARGET_UNAVAILABLE',
        'The target image is unavailable to the calling account.',
        403,
      );
    }
    if ($file->uuid() !== $target['file_uuid']) {
      throw $this->stale();
    }

    $uri = $file->getFileUri();
    $realpath = $this->fileSystem->realpath($uri);
    if ($realpath === FALSE || !is_readable($realpath)) {
      throw new ImageContextException(
        'IMAGE_BYTES_UNAVAILABLE',
        'The verified target image bytes are unavailable.',
        409,
      );
    }

    $bytes = file_get_contents($realpath);
    if ($bytes === FALSE || $bytes === '') {
      throw new ImageContextException(
        'IMAGE_BYTES_UNAVAILABLE',
        'The verified target image bytes are unavailable.',
        409,
      );
    }

    $mime_type = (string) $file->getMimeType();
    if (!str_starts_with($mime_type, 'image/')) {
      throw new ImageContextException(
        'IMAGE_TYPE_INVALID',
        'The verified file is not an image.',
        409,
      );
    }

    $image = $this->imageFactory->get($uri);
    $width = NULL;
    $height = NULL;
    if ($image->isValid()) {
      $width = $image->getWidth() ?: NULL;
      $height = $image->getHeight() ?: NULL;
    }

    $body_plain = '';
    if ($node->hasField('body')) {
      $body = $node->get('body');
      if ($body->access('view', $this->currentUser) && !$body->isEmpty()) {
        $body_plain = $this->plainText((string) $body->value);
      }
    }

    $article = [
      'title' => (string) $node->label(),
      'body_plain' => $body_plain,
      'revision_id' => (int) $node->getRevisionId(),
      'content_language' => $node->language()->getId(),
    ];
    $image_metadata = [
      'file_uuid' => $file->uuid(),
      'filename' => $file->getFilename(),
      'mime_type' => $mime_type,
      'width' => $width,
      'height' => $height,
      'byte_length' => strlen($bytes),
      'sha256' => hash('sha256', $bytes),
    ];

    $hash_payload = [
      'schema_version' => 1,
      'target' => $target,
      'article' => $article,
      'image' => $image_metadata + ['representation_kind' => 'data_url'],
      'existing_alt' => $target['existing_alt'],
    ];

    return [
      'schema_version' => 1,
      'target' => $target,
      'article' => $article,
      'image' => $image_metadata + [
        'representation' => [
          'kind' => 'data_url',
          'value' => sprintf(
            'data:%s;base64,%s',
            $mime_type,
            base64_encode($bytes),
          ),
        ],
      ],
      'existing_alt' => $target['existing_alt'],
      'evidence_hash' => 'sha256:' . hash('sha256', $this->canonicalJson($hash_payload)),
      'collected_at' => gmdate('Y-m-d\TH:i:s\Z'),
    ];
  }

  /**
   * @param array<string, mixed> $target
   */
  private function validateTargetShape(array $target): void {
    $keys = array_keys($target);
    sort($keys);
    $expected = self::TARGET_KEYS;
    sort($expected);
    if ($keys !== $expected) {
      throw $this->invalid('Target keys do not match target.schema.json.');
    }

    if (
      $target['schema_version'] !== 1
      || !is_int($target['sequence'])
      || $target['sequence'] < 1
      || $target['sequence'] > 12
      || !is_string($target['node_uuid'])
      || !$this->isValidUuid($target['node_uuid'])
      || !is_int($target['revision_id'])
      || $target['revision_id'] < 1
      || $target['field_name'] !== 'field_image'
      || !is_int($target['delta'])
      || $target['delta'] < 0
      || !is_string($target['file_uuid'])
      || !$this->isValidUuid($target['file_uuid'])
      || !in_array($target['target_state'], ['missing', 'poor'], TRUE)
      || !(is_string($target['existing_alt']) || $target['existing_alt'] === NULL)
    ) {
      throw $this->invalid('Target values do not conform to target.schema.json.');
    }
  }

  /**
   * @param array<string, mixed> $target
   */
  private function assertCurrentFrozenTarget(array $target): void {
    $targets = $this->finder->find();
    $index = $target['sequence'] - 1;
    if (!isset($targets[$index])) {
      throw $this->stale();
    }
    if ($this->canonicalJson($targets[$index]) !== $this->canonicalJson($target)) {
      throw $this->stale();
    }
  }

  private function isValidUuid(string $value): bool {
    return preg_match(
      '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i',
      $value,
    ) === 1;
  }

  private function plainText(string $value): string {
    $value = Html::decodeEntities(strip_tags($value));
    $value = preg_replace('/\s+/u', ' ', $value) ?? $value;
    return trim($value);
  }

  /**
   * Recursively sorts associative keys for a stable JSON hash.
   */
  private function canonicalJson(mixed $value): string {
    $normalized = $this->sortValue($value);
    return json_encode(
      $normalized,
      JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR,
    );
  }

  private function sortValue(mixed $value): mixed {
    if (!is_array($value)) {
      return $value;
    }
    if (array_is_list($value)) {
      return array_map(fn(mixed $item): mixed => $this->sortValue($item), $value);
    }
    ksort($value);
    foreach ($value as $key => $item) {
      $value[$key] = $this->sortValue($item);
    }
    return $value;
  }

  private function invalid(string $message): ImageContextException {
    return new ImageContextException('INVALID_TARGET', $message, 422);
  }

  private function stale(): ImageContextException {
    return new ImageContextException(
      'TARGET_STALE',
      'The target no longer matches the current authorized field usage.',
      409,
    );
  }

}
