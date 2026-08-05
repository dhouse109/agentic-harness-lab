<?php

declare(strict_types=1);

namespace Drupal\agentic_harness_tools\Exception;

/**
 * Sanitized, structured failure from get_recommendation_status().
 */
final class RecommendationStatusException extends \RuntimeException {

  public function __construct(
    public readonly string $toolCode,
    string $message,
    public readonly int $httpStatus,
    public readonly bool $retryable = FALSE,
  ) {
    parent::__construct($message);
  }

}
