<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Service;

use Drupal\agentic_harness_tools\Exception\RecommendationStatusException;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\node\NodeInterface;
use Drupal\user\UserInterface;

/**
 * Read-only status projection for one recommendation record.
 */
final class RecommendationStatusProvider {

  private const REVIEW_STATUSES = [
    'pending',
    'approved',
    'rejected',
  ];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly AccountProxyInterface $currentUser,
  ) {}

  /**
   * @return array{
   *   uuid: string,
   *   revision_id: int,
   *   status: string,
   *   reviewer_username: string|null,
   *   reviewed_at: string|null
   * }
   */
  public function get(string $identifier): array {
    $identifier = trim($identifier);
    if ($identifier === '') {
      throw $this->invalidIdentifier();
    }

    $storage = $this->entityTypeManager->getStorage('node');
    $node = NULL;

    if (preg_match('/^[1-9][0-9]{0,18}$/', $identifier) === 1) {
      $node = $storage->load((int) $identifier);
    }
    elseif ($this->isValidUuid($identifier)) {
      $matches = $storage->loadByProperties(['uuid' => $identifier]);
      $node = $matches === [] ? NULL : reset($matches);
    }
    else {
      throw $this->invalidIdentifier();
    }

    // Use one generic not-found response for missing nodes and wrong bundles.
    if (!$node instanceof NodeInterface || $node->bundle() !== 'alt_text_suggestion') {
      throw new RecommendationStatusException(
        'RECOMMENDATION_NOT_FOUND',
        'The recommendation identifier does not resolve to an available recommendation.',
        404,
      );
    }

    if (!$node->access('view', $this->currentUser)) {
      throw new RecommendationStatusException(
        'RECOMMENDATION_UNAVAILABLE',
        'The recommendation is unavailable to the calling account.',
        403,
      );
    }

    $status = (string) $node->get('field_review_status')->value;
    if (!in_array($status, self::REVIEW_STATUSES, TRUE)) {
      throw new RecommendationStatusException(
        'RECOMMENDATION_STATE_INVALID',
        'The recommendation has an unsupported review state.',
        409,
      );
    }

    $reviewer_username = NULL;
    $reviewed_at = NULL;

    if ($status !== 'pending') {
      $reviewer_id = (int) $node->getRevisionUserId();
      $reviewer = $this->entityTypeManager
        ->getStorage('user')
        ->load($reviewer_id);

      if (!$reviewer instanceof UserInterface || $reviewer->getAccountName() === '') {
        throw new RecommendationStatusException(
          'REVIEW_METADATA_INVALID',
          'The reviewed recommendation lacks valid reviewer metadata.',
          409,
        );
      }

      $reviewer_username = $reviewer->getAccountName();
      $reviewed_at = gmdate(
        'Y-m-d\TH:i:s\Z',
        (int) $node->getRevisionCreationTime(),
      );
    }

    return [
      'uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'status' => $status,
      'reviewer_username' => $reviewer_username,
      'reviewed_at' => $reviewed_at,
    ];
  }

  private function invalidIdentifier(): RecommendationStatusException {
    return new RecommendationStatusException(
      'INVALID_RECOMMENDATION_ID',
      'The recommendation identifier must be a positive node ID or UUID.',
      422,
    );
  }

  private function isValidUuid(string $value): bool {
    return preg_match(
      '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i',
      $value,
    ) === 1;
  }

}
