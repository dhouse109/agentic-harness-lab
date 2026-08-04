<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Service;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

/**
 * Finds exact Drupal image-field usages that need human alt-text review.
 *
 * This service is deterministic and model-free. It reads Drupal state through
 * entity APIs and access checks; it does not mutate content or suggestions.
 */
final class ImageReviewFinder {

  /**
   * Generic alt values deliberately treated as inadequate by the lab.
   *
   * The classifier is intentionally narrow. It catches blank values, filename
   * echoes, and common placeholder labels without attempting semantic quality
   * judgment that belongs in the later model-and-human workflow.
   */
  private const GENERIC_ALT_VALUES = [
    'image',
    'photo',
    'picture',
    'graphic',
    'illustration',
    'icon',
    'placeholder',
    'test image',
    'article image',
    'supporting image',
    'primary image',
    'phase 0 image',
    'phase0 image',
  ];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly AccountProxyInterface $currentUser,
  ) {}

  /**
   * Returns the frozen target-schema shape for every discovered usage.
   *
   * @return array<int, array<string, int|string|null>>
   *   Ordered target records.
   */
  public function find(): array {
    $node_storage = $this->entityTypeManager->getStorage('node');
    $nids = $node_storage->getQuery()
      ->accessCheck(TRUE)
      ->condition('type', 'article')
      ->sort('nid', 'ASC')
      ->execute();

    $targets = [];
    foreach ($node_storage->loadMultiple($nids) as $node) {
      if (!$node instanceof NodeInterface || !$node->access('view', $this->currentUser)) {
        continue;
      }
      if (!$node->hasField('field_image')) {
        continue;
      }
      $field = $node->get('field_image');
      if (!$field->access('view', $this->currentUser)) {
        continue;
      }

      foreach ($field as $delta => $item) {
        $file = $item->entity;
        if (!$file instanceof FileInterface || !$file->access('view', $this->currentUser)) {
          continue;
        }
        $existing_alt = isset($item->alt) ? (string) $item->alt : '';
        $target_state = $this->classify($existing_alt, $file->getFilename());
        if ($target_state === NULL) {
          continue;
        }

        $targets[] = [
          'schema_version' => 1,
          // Assigned after canonical sorting.
          'sequence' => 0,
          'node_uuid' => $node->uuid(),
          'revision_id' => (int) $node->getRevisionId(),
          'field_name' => 'field_image',
          'delta' => (int) $delta,
          'file_uuid' => $file->uuid(),
          'target_state' => $target_state,
          'existing_alt' => $existing_alt,
          // Private sort key, removed before return.
          '_sort_nid' => (int) $node->id(),
        ];
      }
    }

    usort($targets, static function (array $a, array $b): int {
      return [$a['_sort_nid'], $a['delta'], $a['file_uuid']]
        <=> [$b['_sort_nid'], $b['delta'], $b['file_uuid']];
    });

    foreach ($targets as $index => &$target) {
      unset($target['_sort_nid']);
      $target['sequence'] = $index + 1;
    }
    unset($target);

    return $targets;
  }

  /**
   * Classifies only the deterministic states frozen by target.schema.json.
   */
  private function classify(string $alt, string $filename): ?string {
    $normalized = $this->normalize($alt);
    if ($normalized === '') {
      return 'missing';
    }

    $filename_stem = pathinfo($filename, PATHINFO_FILENAME);
    $normalized_full_filename = $this->normalize($filename);
    $normalized_filename = $this->normalize($filename_stem);
    $filename_words = $this->normalize(str_replace(['-', '_'], ' ', $filename_stem));

    if (in_array($normalized, self::GENERIC_ALT_VALUES, TRUE)) {
      return 'poor';
    }
    if (in_array($normalized, [$normalized_full_filename, $normalized_filename, $filename_words], TRUE)) {
      return 'poor';
    }
    if (preg_match('/^(image|photo|picture|graphic|illustration)(\s+\d+)?(?:\.(?:png|jpe?g|gif|webp))?$/u', $normalized) === 1) {
      return 'poor';
    }
    if (mb_strlen($normalized) <= 3) {
      return 'poor';
    }

    return NULL;
  }

  private function normalize(string $value): string {
    $value = trim($value);
    $value = preg_replace('/\s+/u', ' ', $value) ?? $value;
    return mb_strtolower($value);
  }

}
