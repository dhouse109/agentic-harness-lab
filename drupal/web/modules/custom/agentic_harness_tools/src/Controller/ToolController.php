<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Controller;

use Drupal\agentic_harness_tools\Service\ImageReviewFinder;
use Drupal\Core\Controller\ControllerBase;
use Drupal\Component\Uuid\UuidInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;

/**
 * HTTP boundary for deterministic shared substrate operations.
 */
final class ToolController extends ControllerBase {

  public function __construct(
    private readonly ImageReviewFinder $finder,
    private readonly UuidInterface $uuid,
  ) {}

  public static function create(ContainerInterface $container): self {
    return new self(
      $container->get('agentic_harness_tools.image_review_finder'),
      $container->get('uuid'),
    );
  }

  public function findImagesNeedingReview(Request $request): JsonResponse {
    $correlation_id = $this->correlationId($request);

    try {
      $targets = $this->finder->find();
      $missing = count(array_filter($targets, static fn(array $target): bool => $target['target_state'] === 'missing'));
      $poor = count(array_filter($targets, static fn(array $target): bool => $target['target_state'] === 'poor'));

      // Phase 0 is deliberately pinned to the 12-target fixture. Fail closed if
      // Drupal state drifts rather than returning a schema-incompatible success.
      if (count($targets) !== 12 || $missing !== 9 || $poor !== 3) {
        return new JsonResponse($this->errorEnvelope(
          $correlation_id,
          'DISCOVERY_CARDINALITY_MISMATCH',
          sprintf('Expected 12 targets (9 missing, 3 poor); discovered %d (%d missing, %d poor).', count($targets), $missing, $poor),
          FALSE,
        ), 409);
      }

      return new JsonResponse([
        'schema_version' => 1,
        'tool_name' => 'find_images_needing_review',
        'ok' => TRUE,
        'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
        'correlation_id' => $correlation_id,
        'data' => [
          'targets' => $targets,
          'total_count' => 12,
        ],
        'error' => NULL,
      ], 200, ['Cache-Control' => 'no-store, private']);
    }
    catch (\Throwable $exception) {
      $this->getLogger('agentic_harness_tools')->error(
        'find_images_needing_review failed: @message',
        ['@message' => $exception->getMessage()],
      );
      return new JsonResponse($this->errorEnvelope(
        $correlation_id,
        'DISCOVERY_FAILED',
        'The deterministic discovery operation failed. Review Drupal logs for the local diagnostic.',
        TRUE,
      ), 500);
    }
  }

  private function correlationId(Request $request): string {
    $candidate = trim((string) $request->headers->get('X-Correlation-ID', ''));
    if ($candidate !== '' && preg_match('/^[A-Za-z0-9._:-]{1,128}$/', $candidate) === 1) {
      return $candidate;
    }
    return 'step17-' . $this->uuid->generate();
  }

  /**
   * @return array<string, mixed>
   */
  private function errorEnvelope(string $correlation_id, string $code, string $message, bool $retryable): array {
    return [
      'schema_version' => 1,
      'tool_name' => 'find_images_needing_review',
      'ok' => FALSE,
      'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
      'correlation_id' => $correlation_id,
      'data' => NULL,
      'error' => [
        'code' => $code,
        'message' => $message,
        'retryable' => $retryable,
      ],
    ];
  }

}
