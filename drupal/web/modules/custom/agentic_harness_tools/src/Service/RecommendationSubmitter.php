<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Service;

use Drupal\agentic_harness_tools\Exception\RecommendationSubmissionException;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Lock\LockBackendInterface;
use Drupal\Core\Session\AccountProxyInterface;
use Drupal\file\FileInterface;
use Drupal\node\NodeInterface;

/**
 * Creates one pending recommendation record without mutating source content.
 */
final class RecommendationSubmitter {

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly AccountProxyInterface $currentUser,
    private readonly RecommendationValidator $validator,
    private readonly LockBackendInterface $lock,
  ) {}

  /**
   * @param array<string, mixed> $input
   *
   * @return array<string, mixed>
   */
  public function submit(array $input): array {
    $validated = $this->validator->validate($input);
    $recommendation = $validated['recommendation'];
    $target_node = $validated['target_node'];
    $target_file = $validated['target_file'];

    $lock_name = 'agentic_harness_tools.submit.' . hash(
      'sha256',
      $this->canonicalJson($this->identity($recommendation)),
    );
    if (!$this->lock->acquire($lock_name, 30.0)) {
      throw new RecommendationSubmissionException(
        'SUBMISSION_BUSY',
        'Another request is processing the same recommendation identity.',
        409,
        TRUE,
      );
    }

    try {
      // Verify again inside the idempotency lock immediately before mutation.
      $validated = $this->validator->validate($recommendation);
      $recommendation = $validated['recommendation'];
      $target_node = $validated['target_node'];
      $target_file = $validated['target_file'];

      $existing = $this->findExisting(
        $recommendation,
        $target_node,
        $target_file,
      );
      if (count($existing) > 1) {
        throw new RecommendationSubmissionException(
          'IDEMPOTENCY_STATE_INVALID',
          'More than one recommendation exists for the same run and target identity.',
          409,
        );
      }
      if (count($existing) === 1) {
        $node = reset($existing);
        if (!$node instanceof NodeInterface) {
          throw new RecommendationSubmissionException(
            'IDEMPOTENCY_STATE_INVALID',
            'The existing recommendation could not be loaded.',
            409,
          );
        }
        return $this->replayOrConflict($node, $recommendation);
      }

      $access_handler = $this->entityTypeManager->getAccessControlHandler('node');
      if (!$access_handler->createAccess(
        'alt_text_suggestion',
        $this->currentUser,
      )) {
        throw new RecommendationSubmissionException(
          'CREATE_ACCESS_DENIED',
          'The calling account may not create recommendation records.',
          403,
        );
      }

      $storage = $this->entityTypeManager->getStorage('node');
      $node = $storage->create([
        'type' => 'alt_text_suggestion',
        'title' => sprintf(
          'Alt text recommendation: %s target %d (%s)',
          $recommendation['source_framework'],
          $recommendation['target']['sequence'],
          $recommendation['run_id'],
        ),
        'status' => FALSE,
        'uid' => (int) $this->currentUser->id(),
        'field_target_node' => ['target_id' => (int) $target_node->id()],
        'field_target_revision' => $recommendation['target']['revision_id'],
        'field_target_field' => $recommendation['target']['field_name'],
        'field_target_delta' => $recommendation['target']['delta'],
        'field_target_file' => ['target_id' => (int) $target_file->id()],
        'field_proposed_alt' => $recommendation['proposed_alt_text'],
        'field_review_status' => 'pending',
        'field_source_framework' => $recommendation['source_framework'],
        'field_run_id' => $recommendation['run_id'],
        'field_evidence_hash' => $recommendation['evidence_hash'],
      ]);
      if (!$node instanceof NodeInterface) {
        throw new RecommendationSubmissionException(
          'RECOMMENDATION_CREATE_FAILED',
          'Drupal did not create a recommendation entity instance.',
          500,
          TRUE,
        );
      }

      $node->setNewRevision(TRUE);
      $node->setRevisionUserId((int) $this->currentUser->id());
      $node->setRevisionCreationTime(time());
      $node->setRevisionLogMessage(
        $this->revisionLog($recommendation),
      );
      $node->save();

      // A successful save must produce exactly one row for the idempotency key.
      $persisted = $this->findExisting(
        $recommendation,
        $target_node,
        $target_file,
      );
      if (count($persisted) !== 1) {
        throw new RecommendationSubmissionException(
          'SUBMISSION_VERIFICATION_FAILED',
          'Recommendation persistence did not produce exactly one identity record.',
          500,
          TRUE,
        );
      }

      $saved = reset($persisted);
      if (!$saved instanceof NodeInterface) {
        throw new RecommendationSubmissionException(
          'SUBMISSION_VERIFICATION_FAILED',
          'The saved recommendation could not be reloaded.',
          500,
          TRUE,
        );
      }

      return $this->result($saved, $recommendation);
    }
    finally {
      $this->lock->release($lock_name);
    }
  }

  /**
   * @param array<string, mixed> $recommendation
   * @param \Drupal\node\NodeInterface $target_node
   * @param \Drupal\file\FileInterface $target_file
   *
   * @return array<int, \Drupal\node\NodeInterface>
   */
  private function findExisting(
    array $recommendation,
    NodeInterface $target_node,
    FileInterface $target_file,
  ): array {
    $storage = $this->entityTypeManager->getStorage('node');
    $ids = $storage->getQuery()
      ->accessCheck(FALSE)
      ->condition('type', 'alt_text_suggestion')
      ->condition('field_source_framework.value', $recommendation['source_framework'])
      ->condition('field_run_id.value', $recommendation['run_id'])
      ->condition('field_target_node.target_id', (int) $target_node->id())
      ->condition('field_target_revision.value', $recommendation['target']['revision_id'])
      ->condition('field_target_field.value', $recommendation['target']['field_name'])
      ->condition('field_target_delta.value', $recommendation['target']['delta'])
      ->condition('field_target_file.target_id', (int) $target_file->id())
      ->sort('nid', 'ASC')
      ->range(0, 3)
      ->execute();

    return array_values(array_filter(
      $storage->loadMultiple($ids),
      static fn(mixed $node): bool => $node instanceof NodeInterface,
    ));
  }

  /**
   * @param array<string, mixed> $recommendation
   *
   * @return array<string, mixed>
   */
  private function replayOrConflict(
    NodeInterface $node,
    array $recommendation,
  ): array {
    if ((string) $node->get('field_review_status')->value !== 'pending') {
      throw new RecommendationSubmissionException(
        'RECOMMENDATION_ALREADY_REVIEWED',
        'The existing recommendation has already received a human decision.',
        409,
      );
    }

    $matches = (
      (string) $node->get('field_proposed_alt')->value
        === $recommendation['proposed_alt_text']
      && (string) $node->get('field_evidence_hash')->value
        === $recommendation['evidence_hash']
      && (string) $node->getRevisionLogMessage()
        === $this->revisionLog($recommendation)
      && !$node->isPublished()
    );
    if (!$matches) {
      throw new RecommendationSubmissionException(
        'IDEMPOTENCY_CONFLICT',
        'The same run and target identity already exists with different submission data.',
        409,
      );
    }

    return $this->result($node, $recommendation);
  }

  /**
   * @param array<string, mixed> $recommendation
   *
   * @return array<string, mixed>
   */
  private function result(
    NodeInterface $node,
    array $recommendation,
  ): array {
    return [
      'node_id' => (int) $node->id(),
      'uuid' => $node->uuid(),
      'revision_id' => (int) $node->getRevisionId(),
      'status' => 'pending',
      'source_framework' => $recommendation['source_framework'],
      'run_id' => $recommendation['run_id'],
      'target' => $recommendation['target'],
    ];
  }

  /**
   * @param array<string, mixed> $recommendation
   *
   * @return array<string, mixed>
   */
  private function identity(array $recommendation): array {
    return [
      'source_framework' => $recommendation['source_framework'],
      'run_id' => $recommendation['run_id'],
      'target' => $recommendation['target'],
    ];
  }

  /**
   * @param array<string, mixed> $recommendation
   */
  private function revisionLog(array $recommendation): string {
    return sprintf(
      'submit_recommendation validator=%s evidence=%s',
      $recommendation['validator_version'],
      $recommendation['evidence_hash'],
    );
  }

  private function canonicalJson(mixed $value): string {
    return json_encode(
      $this->sortValue($value),
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

}
