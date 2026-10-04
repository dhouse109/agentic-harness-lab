#!/usr/bin/env python3
"""Permanent, successor-aware Gate 2C.02 source/evidence auditor."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PREDECESSOR = "03816e141f77820e42486fcbad9db244939cd7a8"
CONTRACT_SHA = "3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6"
STEP01_EVIDENCE = "evidence/gates/gate-2c/contract/gate2c-step01-20260922T113303Z-fd9cdb75"
STEP01_POINTER = "evidence/gates/gate-2c/contract/GATE2C-STEP01-LATEST.txt"
STEP01_MANIFEST_SHA = "ed4444d95412b1450784c09eba80817d532cf7ed6a8ad96cd1bbbef179dd6190"
SOURCE_MANIFEST = "shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt"
REHEARSAL_EVIDENCE_ROOT = "evidence/gates/gate-2c/model-free-rehearsals"
AUTHORIZATION_ROOT = "evidence/gates/gate-2c/model-free-rehearsal-authorizations"
PRESERVATION_ROOT = "evidence/gates/gate-2c/model-free-rehearsal-preservation"
ADMISSION_ANCHOR = "shared/contracts/GATE2C-STEP02-ONE-RUN-ADMISSION.json"
ADMISSION_ANCHOR_SIDECAR = "shared/contracts/GATE2C-STEP02-ONE-RUN-ADMISSION.sha256"
ADMISSION_ANCHOR_SHA = "07c9c6356efd9c5b0acbf6af09bbd975c0544e2a3598d6cb50b4dbff9ded57e3"
REPLACEMENT_ADMISSION_ANCHOR = "shared/contracts/GATE2C-STEP02-OFFLINE-REHEARSAL-REPLACEMENT-ADMISSION.json"
REPLACEMENT_ADMISSION_ANCHOR_SIDECAR = "shared/contracts/GATE2C-STEP02-OFFLINE-REHEARSAL-REPLACEMENT-ADMISSION.sha256"
REPLACEMENT_ADMISSION_SCHEMA = "shared/schemas/gate2c-step02-offline-rehearsal-replacement-admission.schema.json"
REPLACEMENT_ADMISSION_ANCHOR_SHA = "c64b8b2a87e26f402d3077bdb9e2746120ff3bd1aca68f5af716b053a9eca3bd"
CORRECTED_ADMISSION_ANCHOR = "shared/contracts/GATE2C-STEP02-CORRECTED-ENVIRONMENT-OFFLINE-REHEARSAL-ADMISSION.json"
CORRECTED_ADMISSION_ANCHOR_SIDECAR = "shared/contracts/GATE2C-STEP02-CORRECTED-ENVIRONMENT-OFFLINE-REHEARSAL-ADMISSION.sha256"
CORRECTED_ADMISSION_SCHEMA = "shared/schemas/gate2c-step02-corrected-environment-offline-rehearsal-admission.schema.json"
CORRECTED_ADMISSION_ANCHOR_SHA = "698af65cf4487c39f23f0e592c450828caac69fb19de9a1484a4e671b4b37daa"
DRUPAL_REPLACEMENT_ADMISSION_ANCHOR = "shared/contracts/GATE2C-STEP02-DRUPAL-REPLACEMENT-ADMISSION.json"
DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SIDECAR = "shared/contracts/GATE2C-STEP02-DRUPAL-REPLACEMENT-ADMISSION.sha256"
DRUPAL_REPLACEMENT_ADMISSION_SCHEMA = "shared/schemas/gate2c-step02-drupal-replacement-admission.schema.json"
DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA = "a88cbe9c4a22a16b137372da01e23aa91041e4910ca478abfba6b6eef38fad23"
DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT = "evidence/gates/gate-2c/drupal-replacement-authorizations"
DRUPAL_FURTHER_REPLACEMENT_ADMISSION = "shared/contracts/GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.json"
DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SCHEMA = "shared/schemas/gate2c-step02-drupal-further-replacement-admission.schema.json"
DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SHA = "045d32e7da973790c430041e95b8b1b849d9c0f1f5ea200a10a85b73470b1995"
DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT = "evidence/gates/gate-2c/drupal-further-replacement-authorizations"
ENVIRONMENT_FINDING = "docs/gates/GATE-2C-STEP02-EXECUTION-ENVIRONMENT-FINDING.md"
PREDECESSOR_SOURCE_MANIFEST_SHA = "4809c2d228010f5a54f2e64fc3d196075c7aa7e1b20e90001f1dc8dcf5572708"
V1_0_14_SOURCE_MANIFEST_SHA = "31d9b9e652276598163b1c43b37f5bffa51ec46cf7f531e280892115115ea096"
HISTORICAL_INVENTORY_SHA = "b123dade4e725e45401e2f580b0ed3987a1af5edd4576490c1c10a09c5a0d3be"
RETAINED_BASELINE_INVENTORY_SHA = "8fb60b7f6c7e29f57b04384d2a974ebe0c8a9379d681a3853b0a664223b5c6d4"
LEGACY_CLASSIFICATION_RUN_ID = "gate2c-step02-offline-20260925T154513Z-5420da48"
LEGACY_CLASSIFICATION_FINALIZATION_SHA = "e5a90548589e1ca94acd9df75394e6265738a61f0783bb262aedcfc948c5042e"
LEGACY_CLASSIFICATION_DIAGNOSTIC_SHA = "3a5437721bd10978684d46c7b942bb597a703fe66cc397bbadbd5a623a4449e1"
LEGACY_CLASSIFICATION_FAILURE_SHA = "007628eb6671458a2cfca55bd7d82cc11758957b529c3a0c3a1db345a52195d6"
REPLACEMENT_FAIL_RUN_ID = "gate2c-step02-offline-20260927T004530Z-8998079d"
REPLACEMENT_FAIL_AUTHORIZATION_SHA = "2a50c586c067f357ec53b810033ca6f472f382a7eb7e9a6cb71cd41824c38317"
REPLACEMENT_FAIL_FINALIZATION_SHA = "29844e2e83464780aba02720776249bd03f886ea8bb3aa8e9ac767040643f4d4"
CORRECTED_STARTUP_EXECUTION_ID = "gate2c-step02-corrected-startup-20260930T214717Z-1354ab5e"
CORRECTED_STARTUP_PRESERVATION_SHA = "7bc109779f0e29e1d7e664679b17bced2cbb83294ecc702735687c888bea2392"
DIAGNOSTIC_PRESERVATIONS = {
    "gate-2c-step02-crewai-representative-entry-boundary-diagnostic-v1.0.0-result-preservation-v1.0.0": "1a68e0b4ff5ee732efae0f96f4ad28afe35853089bcb96069801cb0ee40a76a8",
    "gate-2c-step02-crewai-untraced-representative-entry-boundary-diagnostic-v1.0.0-result-preservation-v1.0.0": "2ed20502e629f1215193b2d64ba599d3b80e32d4039039a4ddfcb266a73602c2",
    "gate-2c-step02-crewai-preimport-only-representative-entry-boundary-diagnostic-v1.0.0-result-preservation-v1.0.0": "46eb1ea574ef88309238ebe37f4168e4083444765a6ecda21972d6f5d11c69bc",
    "gate-2c-step02-crewai-tracing-only-representative-entry-boundary-diagnostic-v1.0.0-result-preservation-v1.0.0": "e95877b9d170c1a75659ffe3e3508e335a2ff7ac11ef4845b60d2b17d67b792c",
    "gate-2c-step02-crewai-flow-started-future-bridge-microprobe-v1.0.0-result-preservation-v1.0.0": "00c2c67890b7b3909cbf327054311bbc2211d23af10949a337d88076d83dfe66",
    "gate-2c-step02-cpython-cross-thread-event-loop-wakeup-control-v1.0.0-result-preservation-v1.0.0": "71db704fe5253743c89bb1d968653e7efa47ed18244b5d1d71d5d494b085f7e8",
    "gate-2c-step02-crewai-corrected-environment-representative-startup-verification-v1.0.0-result-preservation-v1.0.0": "5b012d0f6d1b9d4d44aeb82e86797ab33a8b96beb2442e6454edf6bbb3dfde26",
    "gate-2c-step02-crewai-corrected-environment-representative-startup-verification-v1.0.1-result-preservation-v1.0.0": CORRECTED_STARTUP_PRESERVATION_SHA,
}
DECISION_ROOT = "evidence/gates/gate-2c/crewai-recovery-decisions"
DECISION_ID = "gate2c-step02-crewai-recovery-architecture-decision-20260930T224649Z-24c7b158"
DECISION_PATH = f"{DECISION_ROOT}/{DECISION_ID}.json"
DECISION_SCHEMA = "shared/schemas/gate2c-step02-crewai-decision.schema.json"
CORRECTED_PASS_RUN_ID = "gate2c-step02-offline-20260930T222029Z-24c7b158"
CORRECTED_PASS_AUTHORIZATION_SHA = "1d70d9889561400ce6d9f002daab38113fb6ffc57f4f75cb120bfb3e9115f560"
CORRECTED_PASS_RUNTIME_BINDING_SHA = "b0a1ff3725c2613a892b0a540322f779d401bcbebcc1bf893c139a3ba6599fd6"
CORRECTED_PASS_ALLOCATION_PREFLIGHT_SHA = "7c99feb0985ab0dd21f0978e7ce8154392939c0520c53edf206bcde05280c69f"
CORRECTED_PASS_EXECUTION_PREFLIGHT_SHA = "68114bfe5a4cc3b213d58b7fd83c21911c0d8e3cb1551743c2c581d963c97ec9"
CORRECTED_PASS_EVIDENCE_MANIFEST_SHA = "730b892d232a3dea7e77e4391b7beec5d40e807b76f99b13bb0036ae00cf74ca"
CORRECTED_PASS_FINALIZATION_SHA = "d882c8339025c1ba7e510abb19984fc4724e2a594a190760c07f95db034fd8d8"
CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA = "8a74aa96e78722a989c186b0aa993eaab87c0b84e86ed06a77b60e34542d58ff"
HUMAN_DECISION_GOVERNANCE_SOURCE_MANIFEST_SHA = "dc3e2547b2b04ade752914e05712794f19f3647898ceed2d412941c2d83e494b"
HUMAN_DECISION_REPAIR_SOURCE_MANIFEST_SHA = "639131be0b0e273ba6bedeb3f5a8a51855e8655f445daa74193d84eecb956f31"
HUMAN_DECISION_REPAIR_AUDIT_SHA = "2ee67906fc5cc41923b333e3a7749297079c07b3c5f311372e3dfa39468a2b8d"
HUMAN_DECISION_SHA = "9b46330e3f9dd47bd4c8b7835db928335bde2447ca8825673cef77b9df6e7d1e"
HUMAN_DECISION_PACKAGE = "gate-2c-step02-crewai-recovery-architecture-human-decision-v1.0.0"
HUMAN_DECISION_PACKAGE_MANIFEST_SHA = "9a6faccd80e0ad0ad12272a0e3fb41b38373e87cf86277faceb53c42e4f36a2c"
HUMAN_DECISION_PACKAGE_PAYLOAD_MANIFEST_SHA = "714074407bd4d74db365df95edc507b8fca39908a359bf9d634cb26128919fc9"
HUMAN_DECISION_PACKAGE_CHECKSUM_MANIFEST_SHA = "99dd2957e25ed6a0a74eaaf40452260951dd3152d00100e9c54875faec123a6c"
HUMAN_DECISION_REPAIR_PACKAGE = "gate-2c-step02-crewai-recovery-architecture-human-decision-v1.0.2"
HUMAN_DECISION_REPAIR_PACKAGE_MANIFEST_SHA = "381604322742c9759248ff96f2e12e1cc9ebbed22406ae0e486f8bca2041f8e3"
HUMAN_DECISION_REPAIR_PACKAGE_PAYLOAD_MANIFEST_SHA = "57cb839cf5c3cc1ce9d901ebbb83fb2dd82d6d63574acf4ef3370f323cbaf776"
HUMAN_DECISION_REPAIR_PACKAGE_CHECKSUM_MANIFEST_SHA = "3ab7ac27619c6226c57764f7c092fc03f405cbb5dbd6f74603c83112160d1912"
DRUPAL_RESET_SUPPORT_PACKAGE = "gate-2c-step02-drupal-reset-model-free-proof-v1.0.1"
FAILED_START_REPAIR_PACKAGE = "gate-2c-step02-drupal-failed-start-repair-and-replacement-admission-v1.0.0"
PROCESS_IDENTITY_REPAIR_PACKAGE = "gate-2c-step02-drupal-process-identity-and-further-replacement-admission-v1.0.1"
POST_SIGKILL_REPAIR_PACKAGE = "gate-2c-step02-drupal-post-sigkill-termination-and-missed-immediate-governance-v1.0.0"
POST_EXPIRY_PARTIAL_PACKAGE = "gate-2c-step02-drupal-post-expiry-partial-observation-contract-v1.0.0"
CURRENT_INSTALLED_SOURCE_MANIFEST_SHA = "851b9224fe6caa3344a216fc0ea59c0c3875ee1ec55f4f685131dc6b338144c5"
DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA = "2c634fe8a719cf453668d2c19aab3131696f84667d073221775c3bd81933e768"
POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA = "2d41065f108edc37c0146d8cad7565cea4ee58f340d4df080eb4a59f6defaac8"
POST_EXPIRY_PARTIAL_PREDECESSOR_SOURCE_MANIFEST_SHA = "743a39862997e9924ada9f3f1a7b07a90031d474a3ee699cfffce1e896e2f2a7"
FAILED_DRUPAL_RUN_ID = "gate2c-step02-drupal-20261001T173201Z-545a1ba2"
FAILED_DRUPAL_FAMILY_AGGREGATE_SHA = "1014dacee5194fed8a2c696145d792898d5c9b9399f20c548bdd6e6cd4137714"
FAILED_DRUPAL_EVIDENCE = {
    "FAILED-ATTEMPT.json": "0301fcb645d151ca9feaa82d233c7f98483d3e30bf089aa0789b65ea6dd3ddea",
    "authorization-ledger.json": "ff713910f136b309122747dda7c161e74413b3e8714343272a0c7028d558a760",
}
FAILED_DRUPAL_RUNTIME = {
    "control/expected-host-pid.txt": "0404ecadea447837d1fbe05b41c7a14dafa76c3b6713eccc7f92252bb1d837c5",
    "kill-command.json": "3ea3c7ce75d356913333752af2328801124b819602e618a7378bf4b25e0a3b0b",
    "process-check-command.json": "d3c3271e1288c24b8215b0fa9ae55fff768a31ca7e0464a8e5f89a1b5d18c212",
    "worker-command.json": "f246dd35435059ecce6f79845a9de9983b9d0276f95acb5ab2aa37e5d2517a2b",
}
FAILED_DRUPAL_REPLACEMENT_RUN_ID = "gate2c-step02-drupal-20261001T225458Z-c5d0e6b2"
FAILED_DRUPAL_REPLACEMENT_ADMISSION_SHA = "7cf5ec3fc346632fe121e9154d76e7d6d6f009e053fec8e1aed3a45626a774cf"
FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA = "6ec105136d47f8b25a271c0950ff11984709b7e876e207b45dad7805ccde33c0"
FAILED_DRUPAL_REPLACEMENT_EVIDENCE = {
    "FAILED-ATTEMPT.json": "aabb4a4a5eeab09bb67676393f2b733e1225bd3a0149b5fb6b22eaeb04a112db",
    "authorization-ledger.json": "1bb3332826eb514780093d304caff5a956ffffcfa56b88b2d02546480558f3af",
    "drupal-pre-seam-diagnostic.json": "1ea434c9823a1df30b9e13891ab0f784ab060ea46c04834daa5f21b7a1ef3c04",
}
FAILED_DRUPAL_REPLACEMENT_RUNTIME = {
    "control/expected-host-pid.txt": "6c754b0616340013570400464f68f0e3e73cfc91cbd65e5c2d28d5d0a6770754",
    "control/midpoint.json": "925b6c396b399f3237d5daabdc5a5ae4ea326459342812f5623bc0d9e6e8e97d",
    "control/seam-ready.json": "f84a32479a26195f5fd600c10882a34430d9acc5c6daf877389cb6015b121f09",
    "kill-command.json": "3ea3c7ce75d356913333752af2328801124b819602e618a7378bf4b25e0a3b0b",
    "process-check-command.json": "87494badb3a727c5fba0e068bb07845f8bc6ec499e2ac4ed43f0810fde1f869d",
    "worker-command.json": "b82cb0c0dedd5ba75bc303022b996dd3b240e39b93318d19f6c3486b1a300ccf",
}
FINAL_FAILED_DRUPAL_RUN_ID = "gate2c-step02-drupal-20261002T132121Z-a54c7a7a"
FINAL_FAILED_DRUPAL_ADMISSION_SHA = "15e66d4f70ed74a3921903cbb6134b8986ffabaf2644e08c754465bc3ad58c5c"
FINAL_FAILED_DRUPAL_AGGREGATE_SHA = "cdd180a1c88de2fab50766e7bb82644dfd47fd51b57cca9a412985f15a67b08e"
FINAL_FAILED_DRUPAL_EVIDENCE = {
    "FAILED-ATTEMPT.json": "c405e0cdab7b20f2ab19fb8234b839984929fd7934bdb0589ea4c9b4b4d80ba9",
    "authorization-ledger.json": "2437097210950456800c7b1974247a34895e59f336c30e6188e0e8f69507df98",
    "drupal-pre-kill-process-scan.json": "155d29c317889045d42c0f48ea5a324cb50076cda1ca0fb8a6fc1c3e03183797",
}
FINAL_FAILED_DRUPAL_RUNTIME = {
    "control/expected-host-pid.txt": "52c5450b85e75387e94b74bbfb8f6f5a244d445dfe666c673f9cd9f50b51b13e",
    "control/midpoint.json": "8e2729d9531e36832000d28d74f5f90f6ce125199bd4542e2307092461e09bfb",
    "control/seam-ready.json": "826d2f780116e1903556134c051695d798f8f25c512b61abcbb3317e3541eafa",
    "kill-command.json": "3ea3c7ce75d356913333752af2328801124b819602e618a7378bf4b25e0a3b0b",
    "process-check-command.json": "e1a6b3aa1546f7554951b9fa17de619f0b4f968b8f9c624bec5dfa42e96706bf",
    "worker-command.json": "c7466d36900a3a095e3b3823dac1aec1a509b134599f0d7aa49b683166da1e52",
}
FINAL_FAILED_GOVERNANCE = "shared/contracts/GATE2C-STEP02-DRUPAL-FINAL-FAILED-ATTEMPT-GOVERNANCE.json"
FINAL_FAILED_GOVERNANCE_SIDECAR = "shared/contracts/GATE2C-STEP02-DRUPAL-FINAL-FAILED-ATTEMPT-GOVERNANCE.sha256"
FINAL_FAILED_GOVERNANCE_SCHEMA = "shared/schemas/gate2c-step02-drupal-final-failed-attempt-governance.schema.json"
FINAL_FAILED_GOVERNANCE_SHA = "a7460b1d6a7d3c71cddfefe218ff287328e661a56e3daf5ee9257883832f17c1"
POST_EXPIRY_PARTIAL_CONTRACT = "shared/contracts/GATE2C-STEP02-DRUPAL-POST-EXPIRY-PARTIAL-OBSERVATION-CONTRACT.json"
POST_EXPIRY_PARTIAL_CONTRACT_SIDECAR = "shared/contracts/GATE2C-STEP02-DRUPAL-POST-EXPIRY-PARTIAL-OBSERVATION-CONTRACT.sha256"
POST_EXPIRY_PARTIAL_SCHEMA = "shared/schemas/gate2c-step02-drupal-post-expiry-partial-observation.schema.json"
POST_EXPIRY_PARTIAL_CONTRACT_SHA = "2de52a5778e80cc58e87194cd0b32e265e116e2ce239cd3e908632d47b0796ec"
POST_EXPIRY_PARTIAL_EVIDENCE_ROOT = "evidence/gates/gate-2c/drupal-post-expiry-partial-observations"
DRUPAL_RESET_SUPPORT_UPDATE_PATHS = (
    "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    "scripts/gate2c_step02_audit.py",
    "scripts/gate2c_step02_certify.py",
    "scripts/gate2c_step02_rehearsal.py",
    "scripts/gate2c_step02_reset_rehearsal.py",
    "scripts/gate2c_step02_supervisor.py",
    "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh",
    SOURCE_MANIFEST,
)
HISTORICAL_PROTECTED_SOURCE_PATHS = {
    "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    "scripts/gate2c_step02_supervisor.py",
}
PROTECTED_STATE_FINGERPRINT = "ed349b54ff1d657c81253512470cef4358781efeaf2f208a33c8ea4802da654f"
LATEST_POINTER_FINGERPRINT = "2d82dbe147093c667750019146156e8419b6ec8e13e52d7bdea9bd8197cd5c07"
ENVIRONMENT_FINDING_SHA = "145c21ffe8382cab569244be865ea73ba1661bdb03846cc3987b7b667bbab622"
EXTERNAL_PACKAGE_ROOT = Path("/home/dhouse109/projects/agentic-harness-package-staging")
REHEARSAL_RUN = re.compile(r"^gate2c-step02-(offline|startup|async|memory|drupal|reset)-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$")
QUARANTINED_FAILED_ATTEMPTS = {
    "gate2c-step02-offline-20260922T174202Z-35a22675": {
        "FAILED-ATTEMPT.json": "5e5ea42bd90e8e8cc2cf9f02f9b97383e6426481eb36b6858718c998b6988016",
        "authorization-ledger.json": "6226a2c0dc38cf76d3994301e5b337e3bd216db5709f3b4d592bc6ca4ee0ad65",
        "langgraph-termination.json": "e592f9a5105f418c00c29280081df005d32e2f7bfaf3a6c8028a903d9aaaceaa",
    },
    "gate2c-step02-offline-20260922T213931Z-9f3c7a21": {
        "FAILED-ATTEMPT.json": "c71529c22488b3dfc3b4eea839d1e1c22280a359561e35cd445c978b60bb9157",
        "authorization-ledger.json": "d69055f531c85a3eade4e29e367df2d237510ae1b12a0cfd06f597ad81a4e463",
        "langgraph-recovery.json": "11150e4c202833d14602800def3f878cbb9e81427fb2a59f2b708824c845a476",
        "langgraph-termination.json": "cf174147403a321f4afffe3bec3d12db6413ac782ced6554490d47dcddd080e0",
    },
    "gate2c-step02-offline-20260923T105822Z-ba36ceed": {
        "FAILED-ATTEMPT.json": "7ce0bdf9f32b6d7769686557bc69795fbe599df46f1be01f93a6273c430d7f25",
        "authorization-ledger.json": "87499e945dbf6a9afe1a01bd6b86edf42d8d46b886e90a4abd9d347369608923",
        "langgraph-recovery.json": "23d5b24da3df049f91f0ef38fc26cf125301486a893c95df8808738837292574",
        "langgraph-termination.json": "43bc33793a3d1215408a83249e0eb6075145ff2097800877eb91e7bdfd381636",
    },
    "gate2c-step02-startup-20260923T124207Z-930eee56": {
        "FAILED-ATTEMPT.json": "a10ab8058da1fa26254c791f4a4040a076da7534409993c1809e6b8252d5310d",
        "authorization-ledger.json": "e16d86aebbd70c3f43929a78f307579adfb6aead298b8e7810d8f658fca3e72e",
    },
    "gate2c-step02-startup-20260923T134027Z-e5acfebb": {
        "FAILED-ATTEMPT.json": "f826742a2227b1fd3d62150544bcc44e6a39b8264ece0adc06a10dd2e7398076",
        "authorization-ledger.json": "532840c59d5f8bcb1bb62a8c1675d71d515be84df123ac5dbf27031a8c3de955",
    },
    "gate2c-step02-startup-20260923T144053Z-06d5f691": {
        "FAILED-ATTEMPT.json": "f23753ea515cc7c04838745a499547cfb61ee40611fe7638494e9047e6b39424",
        "authorization-ledger.json": "39f75329ecad1252c3e680ae826ec6f4c3baeada3c7dd000b37797c487e72e59",
    },
    "gate2c-step02-startup-20260923T184826Z-76fef1dc": {
        "FAILED-ATTEMPT.json": "92f69d063eba891a439525b785580b666b201e5efd1abb2791486cdacac31842",
        "authorization-ledger.json": "ede98f1641ddd37be4c14d6421e278e32b3f67ba7ddab136c242442e003dd286",
    },
    "gate2c-step02-async-20260923T235257Z-392b56a7": {
        "FAILED-ATTEMPT.json": "aea0541db4283b633604891b327193ecd4f095114d888e82d37b419212640b2e",
        "authorization-ledger.json": "7b6435b0d28c780bb3b1f9fe6ca57e10ddfd7c3b4364b3fda4128ad47b0ec766",
        "lancedb-async-diagnostic.json": "ee47eb7c4344270b1a6fe0336776fe105e3e2b35556510b087822b8b0f30fc7f",
        "runtime-inventory.json": "ab5790a472ebb91426d8f79ec8bf1231416d2def3abba59e4dba0ed1a4fef7ee",
    },
    "gate2c-step02-memory-20260924T124150Z-b5d60fa6": {
        "FAILED-ATTEMPT.json": "8ec5c60397716460f87031f7cda29928be2d52e8dd00a3f6d4eccab17756f04f",
        "authorization-ledger.json": "7729745eb92a76e7ea8291430393da46e2f8b2111b93c3a598836811a4980771",
        "lancedb-memory-async-diagnostic.json": "efaf0b8263342b81bf6ce89e17b5ff5e69051eb9d4d14e764ce4ec73f81abcb2",
        "runtime-inventory.json": "ff328e52ce6e152a30c43480e58b3e35f65a0ffb0ebf8b1af33d16b79007d1a5",
    },
    "gate2c-step02-startup-20260924T193318Z-dd57cbc4": {
        "FAILED-ATTEMPT.json": "255902317c373d66f4acef4fc3c672a02f53c75ec86b15763e9820baab30fcb6",
        "authorization-ledger.json": "f0d04ba62b2a305b81a7bc93dc897a0b3f2a8351afca98b51e3ca48929dcf160",
    },
    "gate2c-step02-offline-20260924T203449Z-1ec8feac": {
        "FAILED-ATTEMPT.json": "c6fcdfb82b646f969addea1c00ae6543c875a12021c1eff79840c70b71ecdff9",
        "authorization-ledger.json": "71e7e0f7b092a31029804336b780f6b57f9a2937d32b5e2b0cd3403274a36bf6",
        "crewai-startup-diagnostic.json": "b36392cca453634a4e183965c7bbe01b0d9761520dd28574ffdf04c4d50c325a",
        "langgraph-recovery.json": "746f7b1a87ecb6a656992920cea51ee1986db0a60dfa9335ad011d8895e2bf30",
        "langgraph-termination.json": "6128e82b6450fa2ff00175019a7e34c7f33c5e5631f4000b553230aecafb2391",
    },
}
RUNTIME_ROOT = ".cache/gate2c-step02"
QUARANTINED_RUNTIME_ARTIFACTS = {
    "gate2c-step02-offline-20260922T174202Z-35a22675": {
        "langgraph/expected-host-pid.txt": "aa67a169b0bba217aa0aa88a65346920c84c42447c36ba5f7ea65f422c1fe5d8",
        "langgraph/midpoint.json": "0eb484193184713f10022aaf2d39f81787a44260ea2cab8931bdfe50e57b9b4d",
        "langgraph/seam-ready.json": "6a39dc47598965a5da47c70beb948703af0e01edfd063117a7958bc5ce13eb2f",
        "langgraph/state.sqlite": "7809470f69438fe4b039a5bf86193a3899ffc2be7dc2aae4e088bbea54102c5f",
        "langgraph/state.sqlite-shm": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
        "langgraph/state.sqlite-wal": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "langgraph/worker-command.json": "a8f07e4ded9bbd57c07c2e6d721af0348523a5d55f5b3f63e15d7f6aac6b36cf",
    },
    "gate2c-step02-offline-20260922T213931Z-9f3c7a21": {
        "crewai/expected-host-pid.txt": "076320a2a08267b4c026d06573bba408ea68841e73cdc20e62cce59de165ece3",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "7348d83894b5cd3cefd97e8b92a419d5d63c642c31d2978e02c9ad1b2a71effe",
        "langgraph/checkpoint-verifier-command.json": "b47b952b80dfb107a517398854a4250cab95b4c3c92eb1a67f45fb2e3d0fc541",
        "langgraph/durable-checkpoint.json": "90ea21ddd52540085109f86eefa32e0e395561112e1e82d19559fe14a45916ce",
        "langgraph/expected-host-pid.txt": "06e9d52c1720fca412803e3b07c4b228ff113e303f4c7ab94665319d832bbfb7",
        "langgraph/midpoint.json": "538531dfef8d85e85db14d6800a2fbb686eb9a91664f0c8b33cda677a63b031c",
        "langgraph/seam-ready.json": "23e8984ed25914f4a13b89a1f6fcc0d17eff02fb457532b78f7e498306310b9a",
        "langgraph/state.sqlite": "b822d6c80179496541aff21945d042c4e4c576a11dea815142984d42fadf5848",
        "langgraph/worker-command.json": "da8292b5fc94c30dc45cab779ae11386c88605bb8065c0a7f8ee0ad88f77323c",
    },
    "gate2c-step02-offline-20260923T105822Z-ba36ceed": {
        "crewai/expected-host-pid.txt": "076320a2a08267b4c026d06573bba408ea68841e73cdc20e62cce59de165ece3",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/state.sqlite-shm": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
        "crewai/state.sqlite-wal": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "crewai/worker-command.json": "cfceea5be258bfb548c32e64092a09949f4547bacb2e605a138dd2bf1bb33923",
        "langgraph/checkpoint-verifier-command.json": "631fbe817b520bc2b8bb0da972526b28f12566415d41a385d779bd18ff340ae1",
        "langgraph/durable-checkpoint.json": "b3a3510b32465c230ab2e814ccac76ca3bff0217878198a61a7a7e665b30343f",
        "langgraph/expected-host-pid.txt": "06e9d52c1720fca412803e3b07c4b228ff113e303f4c7ab94665319d832bbfb7",
        "langgraph/midpoint.json": "63c5ddd7ca29866084cb064fc45599ef0147b66420da5cf582ba5cd687723954",
        "langgraph/seam-ready.json": "a4bc565d044c7558f51b4f87d86a7d8cf7dd4bedef666a631247db41359f18e9",
        "langgraph/state.sqlite": "1c91634dc8474cd2f22ad47ff63abc66a509768a826ecf3f624541b739729529",
        "langgraph/worker-command.json": "9664a84e1ab1cef8db0404aaa0dd8b28139a1ce750b836a2978a9b2dec34c748",
    },
    "gate2c-step02-startup-20260923T124207Z-930eee56": {
        "crewai/startup-phases.jsonl": "0bf6c261e4ace1a447cce382d5d7947a1d7fd601531f819f74aaf875bbb30bd2",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "e23bc5a51edf177912d5300df03cfcb2ef1636e0af1020e647f46571d023cbba",
    },
    "gate2c-step02-startup-20260923T134027Z-e5acfebb": {
        "crewai/startup-phases.jsonl": "effd9a3826dbaa2a1dcf30e897e05e0dffcff99d350d363d772ec34baaa53d6b",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "cd58b26ae26dcc948696f4b1ce94777fbf8311a75c499bed924bb95e74673945",
    },
    "gate2c-step02-startup-20260923T144053Z-06d5f691": {
        "crewai/stack-location-summary.json": "174ddacb614fcdab978f1acedcbc6e6fffbb2e609e8252902b1f99d46f925bbf",
        "crewai/stack-locations.jsonl": "1fdc9c133f24712160f3b93aa4ba6f8cea72e2064c9e457ea0411268ce571ffc",
        "crewai/startup-phases.jsonl": "98df28b467f0405417c26ceade48b40aa21f2535b47bf8043a3bea95c17afeb5",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "c2940b950db02a3677d29e9be6cb5e4eed6efb521ec3324a70be10f47e317be6",
    },
    "gate2c-step02-startup-20260923T184826Z-76fef1dc": {
        "crewai/stack-location-summary.json": "d65b75a3e43823c360e7cf2b4e35f7b5866ea98237962a63d092862c1d9a97db",
        "crewai/stack-locations.jsonl": "4c9d5dc91169b31b5081a143d3881b8355e1789ea76d9ddadeea951a75672951",
        "crewai/startup-phases.jsonl": "f868ce62be4ad0b611c79604a8e614e95d938e010dad103187c60db7779dadf2",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "9952c608455da4b5dec4ac5126b670c1896df8d2596be3d3311c4a7708632ba2",
    },
    "gate2c-step02-async-20260923T235257Z-392b56a7": {
        "lancedb-async/async-connect-phases.jsonl": "313def048ee12ae48bd2e691458a84c8e85ecadb76d4b4b4e626956f871c8912",
        "lancedb-async/worker-command.json": "7c254f651e44a982c843bcd1c8b61a90d3ee32b22471a538b591ed1e6d954ebb",
    },
    "gate2c-step02-memory-20260924T124150Z-b5d60fa6": {
        "lancedb-memory-async/memory-async-connect-phases.jsonl": "e88b270cf5362a4c996dd6ad273c9c7cee116fd9924bc67ff3427ded34ab22e4",
        "lancedb-memory-async/worker-command.json": "95271e715ff1353ceb5537d58444578d9fddb41947fdb29f27f79a5a04173249",
    },
    "gate2c-step02-startup-20260924T193318Z-dd57cbc4": {
        "crewai/stack-location-summary.json": "8b7f604f749e78988e80104351108d4f2b2aab8d3c60c62ab7c277935cec2417",
        "crewai/startup-phases.jsonl": "991168f7409cee18c549487505effc190736f936fad8919fa783fc4a233d73d4",
        "crewai/worker-command.json": "50b0011fe0b7f02e5fa0ba84ed836d2fceaa334a45d7ab507a07bdbb991a72ac",
    },
    "gate2c-step02-offline-20260924T203449Z-1ec8feac": {
        "crewai/expected-host-pid.txt": "076320a2a08267b4c026d06573bba408ea68841e73cdc20e62cce59de165ece3",
        "crewai/startup-phases.jsonl": "c06c8325075f5f4975e72e22e34d067dbb498a77e5dc829fd6345125672c44c5",
        "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
        "crewai/worker-command.json": "1aa2be83fe82d3597bcbdae1225f4941655260d585b1b6075b5d84c0ee41721c",
        "langgraph/checkpoint-verifier-command.json": "1606aaa94684ac4c14d163b5ad789f0ae2c4dfee47e29ba9afc283797e7d5fc2",
        "langgraph/durable-checkpoint.json": "e40148daa6648808456553aa26980de16db27b53c06c08563b692bc343e0036d",
        "langgraph/expected-host-pid.txt": "06e9d52c1720fca412803e3b07c4b228ff113e303f4c7ab94665319d832bbfb7",
        "langgraph/midpoint.json": "4c652b66943f1e9a9743638d77b9ba8fd82ed91a44715603834460f3f86e3ff7",
        "langgraph/seam-ready.json": "2e23c8829444f28880763451422fda2659532251eb37204873053f80a79a3b5d",
        "langgraph/state.sqlite": "42eb8102249c62cafe1a0b298053b6330c02f39314a408bd149fa4c27c3fd70e",
        "langgraph/worker-command.json": "18678583db8de9ca65bf7026a889dc3ab5e9aa068f6ad3b344fcaf671903e599",
    },
}
POST_INSPECTION_RUNTIME_ARTIFACTS = {
    "gate2c-step02-offline-20260924T203449Z-1ec8feac": {
        "crewai/state.sqlite-shm": (32768, "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb"),
        "crewai/state.sqlite-wal": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        "langgraph/state.sqlite-shm": (32768, "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb"),
        "langgraph/state.sqlite-wal": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    },
}
ACCEPTED_STARTUP_RUN_ID = "gate2c-step02-startup-20260924T202432Z-b30ac8de"
BASELINE_RUN_IDS = frozenset(QUARANTINED_FAILED_ATTEMPTS) | {ACCEPTED_STARTUP_RUN_ID}
ACCEPTED_STARTUP_EVIDENCE = {
    "authorization-ledger.json": "10f706c382f9c2c03dce67c1d8ec7c6f1630e4be0ae80f1ab7184b40b5cbe4a8",
    "crewai-startup.json": "7fec4da2532dc4f6c3f82148fbff83f7404fc1f3782bfda9e42153cd0c0654e6",
    "evidence-manifest.json": "823395219adabe33a1b2082772ec3256b6b1c2a80c4c75973e9696c635f7ebf3",
    "privacy-scan.json": "22a020ea14c626ddf86833f234e9e7b2ba6f0d4eb5725347cf7d9817f4cde9c0",
    "summary.md": "b5592fc0ff09b3563d765935c21af536a569c51da7db7c6f081e84b1136cb2eb",
}
ACCEPTED_STARTUP_RUNTIME = {
    "crewai/stack-location-summary.json": "d962a4e85c5c20440673c3b663e1ae7ee1f97fcb2d001d21f63ce0bded3882b1",
    "crewai/startup-phases.jsonl": "fc7193992e0ba6ff4e64499a65125a0d8b593c7bd7c94600dad1b6cca0337298",
    "crewai/state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
    "crewai/worker-command.json": "2526ba3be29966ade3587ebf038215f5973a734616cfa69cb64134fc64cf46df",
}
QUARANTINED_RUNTIME_DIRECTORIES = {
    "gate2c-step02-offline-20260922T174202Z-35a22675": {"", "langgraph"},
    "gate2c-step02-offline-20260922T213931Z-9f3c7a21": {"", "crewai", "langgraph"},
    "gate2c-step02-offline-20260923T105822Z-ba36ceed": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
        "crewai/bootstrap/data/agentic-harness-lab/memory", "langgraph",
    },
    "gate2c-step02-startup-20260923T124207Z-930eee56": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
        "crewai/bootstrap/data/agentic-harness-lab/memory",
    },
    "gate2c-step02-startup-20260923T134027Z-e5acfebb": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
        "crewai/bootstrap/data/agentic-harness-lab/memory",
    },
    "gate2c-step02-startup-20260923T144053Z-06d5f691": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
        "crewai/bootstrap/data/agentic-harness-lab/memory",
    },
    "gate2c-step02-startup-20260923T184826Z-76fef1dc": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
        "crewai/bootstrap/data/agentic-harness-lab/memory",
    },
    "gate2c-step02-async-20260923T235257Z-392b56a7": {
        "", "lancedb-async", "lancedb-async/local-lancedb",
    },
    "gate2c-step02-memory-20260924T124150Z-b5d60fa6": {
        "", "lancedb-memory-async",
    },
    "gate2c-step02-startup-20260924T193318Z-dd57cbc4": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab",
    },
    "gate2c-step02-offline-20260924T203449Z-1ec8feac": {
        "", "crewai", "crewai/bootstrap", "crewai/bootstrap/cache",
        "crewai/bootstrap/config", "crewai/bootstrap/data",
        "crewai/bootstrap/data/agentic-harness-lab", "langgraph",
    },
}
REHEARSAL_FILES = {
    "offline": {
        "authorization-ledger.json", "langgraph-termination.json", "langgraph-recovery.json",
        "crewai-termination.json", "crewai-recovery.json", "negative-controls.json",
        "public-api-provenance.json", "privacy-scan.json", "summary.md", "evidence-manifest.json",
    },
    "startup": {
        "authorization-ledger.json", "crewai-startup.json", "privacy-scan.json",
        "summary.md", "evidence-manifest.json",
    },
    "async": {
        "authorization-ledger.json", "lancedb-async-diagnostic.json",
        "runtime-inventory.json", "privacy-scan.json", "summary.md",
        "evidence-manifest.json",
    },
    "memory": {
        "authorization-ledger.json", "lancedb-memory-async-diagnostic.json",
        "runtime-inventory.json", "privacy-scan.json", "summary.md",
        "evidence-manifest.json",
    },
    "drupal": {
        "authorization-ledger.json", "drupal-termination.json", "drupal-immediate.json",
        "drupal-post-expiry.json", "zero-operation-accounting.json", "privacy-scan.json",
        "summary.md", "evidence-manifest.json",
    },
    "reset": {
        "reset-restoration.json", "authorization-ledger.json", "privacy-scan.json",
        "summary.md", "evidence-manifest.json",
    },
}
FREEZES = {
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
    "shared/contracts/GATE2B-CREWAI-FREEZE.json": "74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206",
}
ACCEPTED_CREWAI_MEMORY_SOURCES = {
    "docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md": "58414e67a2527edb402982391b8af78793a19b7bdaab1d86ea2571a6f995a278",
    "crewai/agentic_harness_crewai/__init__.py": "1e795c9dc1415ac91c1972c3cc7706d3e946c23c50ca148802cc28483a803381",
    "crewai/agentic_harness_crewai/canonical_slice.py": "6578900a409a3a6db4bec34f56f2fbaa2bb0602c87f55e596f20272641df9484",
    "crewai/.venv/lib/python3.12/site-packages/crewai/memory/storage/factory.py": "d7e39deda8c1eb0e0ef1e9113e44bec77aeae51d23591a66982375809d60647d",
    "crewai/.venv/lib/python3.12/site-packages/crewai/memory/unified_memory.py": "98e3015cfda600dd18d14dc5cdac4eda2402e1c12bd9df3cb2ef5722abc6acdd",
}
PINNED_CREWAI_TELEMETRY_SOURCES = {
    "crewai/.venv/lib/python3.12/site-packages/crewai/telemetry/telemetry.py": "a28c11bf9bf399075c0aeaafa2c9263516058c401c32bb4723e27ce03f1a4f6c",
    "crewai/.venv/lib/python3.12/site-packages/crewai_core/telemetry.py": "4f67b3ff875580f7d556cda36e8ddd7f3daf42e2c7949e8699901ef1bd20b8a6",
}
SNAPSHOT = "drupal/.ddev/db_snapshots/gate2b-step06-post-step2b05-recovery-20260826T152003Z-mariadb_11.8.zst"
SNAPSHOT_SHA = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
PROTECTED_SHA256 = {
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite": "d0fd3ac373b6af0aace07b7eed6813ebea28ceab37ab47265da2da94a24acff2",
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite-shm": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite-wal": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite": "d760c0167b9cf1ba080317d3bb68a17ce28bdc027d0d2f8c73ffd1c2a9184f12",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite-shm": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite-wal": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "crewai/.runtime/gate2b-step06/crewai-20260827T125501Z-c5381188/flow-state.sqlite": "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa",
    "crewai/.runtime/gate2b-step06/crewai-20260827T174606Z-6249d844/flow-state.sqlite": "acba30a27e301b09354ff367aa6a85bdab2c90abfab258fd0b99f25645ed7f8c",
    "evidence/gates/gate-2b/frozen-batch-activation/LATEST": "4befe3e0d3c36c461a37bfa898777a4720d9223ba7b4c509f2885b2e9db086ff",
    "evidence/gates/gate-2b/frozen-batch-http-readiness/LATEST": "93b237208d205122036120e91326ddafd460bed86f01933207d09e86c6708946",
    "evidence/gates/gate-2b/frozen-batch/LATEST": "7abd87756e7c4320804bda1e9d381131071d4c6cfd080e5ab7c49902b811e4d3",
}
PROTECTED = set(PROTECTED_SHA256)
INSTALLED_SOURCES = {
    ENVIRONMENT_FINDING,
    "docs/gates/GATE-2C-STEP02-SHARED-FAILURE-INJECTOR-AND-MODEL-FREE-REHEARSALS.md",
    "shared/contracts/GATE2C-STEP02-MODEL-FREE-REHEARSAL-PLAN.json",
    "shared/contracts/GATE2C-STEP02-MODEL-FREE-REHEARSAL-PLAN.sha256",
    "shared/contracts/GATE2C-STEP02-ONE-RUN-ADMISSION.json",
    "shared/contracts/GATE2C-STEP02-ONE-RUN-ADMISSION.sha256",
    REPLACEMENT_ADMISSION_ANCHOR,
    REPLACEMENT_ADMISSION_ANCHOR_SIDECAR,
    "shared/schemas/gate2c-step02-model-free-rehearsal.schema.json",
    "shared/schemas/gate2c-step02-crewai-decision.schema.json",
    "shared/schemas/gate2c-step02-one-run-transition.schema.json",
    REPLACEMENT_ADMISSION_SCHEMA,
    CORRECTED_ADMISSION_ANCHOR,
    CORRECTED_ADMISSION_ANCHOR_SIDECAR,
    CORRECTED_ADMISSION_SCHEMA,
    DRUPAL_REPLACEMENT_ADMISSION_ANCHOR,
    DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SIDECAR,
    DRUPAL_REPLACEMENT_ADMISSION_SCHEMA,
    DRUPAL_FURTHER_REPLACEMENT_ADMISSION,
    "shared/contracts/GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.sha256",
    DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SCHEMA,
    FINAL_FAILED_GOVERNANCE,
    FINAL_FAILED_GOVERNANCE_SIDECAR,
    FINAL_FAILED_GOVERNANCE_SCHEMA,
    POST_EXPIRY_PARTIAL_CONTRACT,
    POST_EXPIRY_PARTIAL_CONTRACT_SIDECAR,
    POST_EXPIRY_PARTIAL_SCHEMA,
    "scripts/gate2c_step02_supervisor.py",
    "scripts/gate2c_step02_rehearsal.py",
    "scripts/gate2c_step02_reset_rehearsal.py",
    "scripts/gate2c_step02_audit.py",
    "scripts/gate2c_step02_corrected_environment_preflight.py",
    "scripts/gate2c_step02_certify.py",
    "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh",
    "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    "langchain/agentic_harness_langgraph/gate2c_recovery.py",
    "crewai/agentic_harness_crewai/gate2c_recovery.py",
    "crewai/agentic_harness_crewai/gate2c_lancedb_async_diagnostic.py",
    "crewai/agentic_harness_crewai/gate2c_lancedb_memory_async_diagnostic.py",
}
INSTALL_UPDATE = {
    "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    "scripts/gate2c_step02_supervisor.py",
    "scripts/gate2c_step02_rehearsal.py",
    "scripts/gate2c_step02_audit.py",
    "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh",
    SOURCE_MANIFEST,
}
INSTALL_CREATE = {
    DRUPAL_REPLACEMENT_ADMISSION_ANCHOR,
    DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SIDECAR,
    DRUPAL_REPLACEMENT_ADMISSION_SCHEMA,
}
PROCESS_IDENTITY_INSTALL_CREATE = {
    DRUPAL_FURTHER_REPLACEMENT_ADMISSION,
    "shared/contracts/GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.sha256",
    DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SCHEMA,
}
POST_SIGKILL_INSTALL_UPDATE = {
    "scripts/gate2c_step02_supervisor.py",
    "scripts/gate2c_step02_rehearsal.py",
    "scripts/gate2c_step02_audit.py",
    SOURCE_MANIFEST,
}
POST_SIGKILL_INSTALL_CREATE = {
    FINAL_FAILED_GOVERNANCE,
    FINAL_FAILED_GOVERNANCE_SIDECAR,
    FINAL_FAILED_GOVERNANCE_SCHEMA,
}
POST_EXPIRY_PARTIAL_INSTALL_UPDATE = {
    "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    "scripts/gate2c_step02_rehearsal.py",
    "scripts/gate2c_step02_audit.py",
    "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh",
    SOURCE_MANIFEST,
}
POST_EXPIRY_PARTIAL_INSTALL_CREATE = {
    POST_EXPIRY_PARTIAL_CONTRACT,
    POST_EXPIRY_PARTIAL_CONTRACT_SIDECAR,
    POST_EXPIRY_PARTIAL_SCHEMA,
}
PAYLOAD_PATTERNS = {
    "openai_key": re.compile(r"sk-(?:proj|live)-[A-Za-z0-9_-]{12,}", re.I),
    "auth_header": re.compile(r"Authorization:\s*(?:Basic|Bearer)\s+[A-Za-z0-9+/=_-]{8,}", re.I),
    "data_url": re.compile(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/]{12,}={0,2}", re.I),
    "api_assignment": re.compile(r"OPENAI_API_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", re.I),
}
STRICT = (b"sk-proj-", b"Authorization: Basic ", b"Authorization: Bearer ", b"data:image/", b"OPENAI_API_KEY=")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def verify_manifest(root: Path) -> None:
    value = json.loads((root / "evidence-manifest.json").read_text(encoding="utf-8"))
    entries = value.get("files") or value.get("entries")
    require(isinstance(entries, list), "evidence manifest entries")
    for entry in entries:
        path = root / entry["path"]
        require(path.is_file() and path.stat().st_size == entry["size"] and sha(path) == entry["sha256"], f"evidence drift: {path}")


def verify_path_hashes(root: Path, expected: dict[str, str], label: str) -> None:
    for relative, digest in sorted(expected.items()):
        path = root / relative
        require(path.is_file(), f"{label} path missing: {relative}")
        require(sha(path) == digest, f"{label} path hash drift: {relative}")


def verify_quarantined_runtimes(repo: Path, successor_ids: set[str] | None = None) -> None:
    runtime_root = repo / RUNTIME_ROOT
    require(runtime_root.is_dir() and not runtime_root.is_symlink(), "quarantined runtime root missing")
    identities = {path.name for path in runtime_root.iterdir() if path.is_dir()}
    expected_identities = set(BASELINE_RUN_IDS) | (successor_ids or set())
    require(identities == expected_identities, "exact baseline plus authorized successor runtime identity inventory")
    for run_id, expected in sorted(QUARANTINED_RUNTIME_ARTIFACTS.items()):
        root = runtime_root / run_id
        paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
        directories = {""} | {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()}
        post_inspection = POST_INSPECTION_RUNTIME_ARTIFACTS.get(run_id, {})
        require(not any(path.is_symlink() for path in root.rglob("*")), f"quarantined runtime symlink: {run_id}")
        require(paths == set(expected) | set(post_inspection), f"quarantined runtime file inventory: {run_id}")
        require(directories == QUARANTINED_RUNTIME_DIRECTORIES[run_id], f"quarantined runtime directory inventory: {run_id}")
        verify_path_hashes(root, expected, "quarantined failed-attempt runtime")
        for relative, (size, digest) in sorted(post_inspection.items()):
            path = root / relative
            require(path.is_file(), f"post-inspection SQLite sidecar missing: {relative}")
            require(path.stat().st_size == size, f"post-inspection SQLite sidecar size drift: {relative}")
            require(sha(path) == digest, f"post-inspection SQLite sidecar hash drift: {relative}")

    accepted_root = runtime_root / ACCEPTED_STARTUP_RUN_ID
    accepted_paths = {
        path.relative_to(accepted_root).as_posix()
        for path in accepted_root.rglob("*") if path.is_file()
    }
    require(accepted_paths == set(ACCEPTED_STARTUP_RUNTIME), "accepted startup runtime exact file inventory")
    require(not any(path.is_symlink() for path in accepted_root.rglob("*")), "accepted startup runtime symlink")
    verify_path_hashes(accepted_root, ACCEPTED_STARTUP_RUNTIME, "accepted startup runtime")


def verify_accepted_startup_evidence(repo: Path) -> None:
    root = repo / REHEARSAL_EVIDENCE_ROOT / ACCEPTED_STARTUP_RUN_ID
    require(root.is_dir() and not root.is_symlink(), "accepted startup evidence root")
    names = {path.name for path in root.iterdir() if path.is_file()}
    require(names == set(ACCEPTED_STARTUP_EVIDENCE), "accepted startup evidence exact file inventory")
    verify_path_hashes(root, ACCEPTED_STARTUP_EVIDENCE, "accepted startup evidence")
    verify_manifest(root)


def verify_historical_inventory_anchor(repo: Path) -> None:
    entries: list[dict[str, Any]] = []
    for run_id, files in QUARANTINED_FAILED_ATTEMPTS.items():
        for relative, digest in files.items():
            path = repo / REHEARSAL_EVIDENCE_ROOT / run_id / relative
            entries.append({"class": "historical_evidence", "path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": digest})
    for relative, digest in ACCEPTED_STARTUP_EVIDENCE.items():
        path = repo / REHEARSAL_EVIDENCE_ROOT / ACCEPTED_STARTUP_RUN_ID / relative
        entries.append({"class": "historical_evidence", "path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": digest})
    for run_id, files in QUARANTINED_RUNTIME_ARTIFACTS.items():
        for relative, digest in files.items():
            path = repo / RUNTIME_ROOT / run_id / relative
            entries.append({"class": "historical_runtime", "path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": digest})
    for relative, digest in ACCEPTED_STARTUP_RUNTIME.items():
        path = repo / RUNTIME_ROOT / ACCEPTED_STARTUP_RUN_ID / relative
        entries.append({"class": "historical_runtime", "path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": digest})
    for run_id, files in POST_INSPECTION_RUNTIME_ARTIFACTS.items():
        for relative, (size, digest) in files.items():
            path = repo / RUNTIME_ROOT / run_id / relative
            entries.append({"class": "post_inspection_runtime", "path": path.relative_to(repo).as_posix(), "size": size, "sha256": digest})
    entries.sort(key=lambda item: item["path"])
    require(len(entries) == 110 and canonical_sha(entries) == HISTORICAL_INVENTORY_SHA, "historical 110-file inventory trust anchor")


def validate_startup_stack_runtime(repo: Path, run_id: str) -> str:
    """Validate legacy v1.0.6 or dual-role v1.0.7 records without frame data."""
    from gate2c_step02_supervisor import (
        classify_connection_boundary,
        validate_stack_location_records,
        validate_stack_location_summary,
        validate_startup_phases,
    )

    root = repo / RUNTIME_ROOT / run_id / "crewai"
    require(root.is_dir() and not root.is_symlink(), f"startup diagnostic runtime missing: {run_id}")
    framework_run = f"{run_id}-crewai"
    phases = validate_startup_phases(
        root / "startup-phases.jsonl",
        trial_id=run_id,
        run_id=framework_run,
    )
    validate_stack_location_records(
        root / "stack-locations.jsonl",
        trial_id=run_id,
        run_id=framework_run,
    )
    summary_path = root / "stack-location-summary.json"
    require(summary_path.is_file() and not summary_path.is_symlink(), "stack location summary missing")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validate_stack_location_summary(summary, trial_id=run_id, run_id=framework_run)
    require(
        summary.get("connection_boundary_classification") == classify_connection_boundary(phases),
        "stack summary connection-boundary mismatch",
    )
    scan_evidence(root)
    return sha(summary_path)


def validate_async_runtime(repo: Path, evidence: Path, run_id: str) -> None:
    from gate2c_step02_rehearsal import validate_async_phases, validate_async_result

    root = repo / RUNTIME_ROOT / run_id / "lancedb-async"
    require(root.is_dir() and not root.is_symlink(), f"async diagnostic runtime missing: {run_id}")
    inventory_path = evidence / "runtime-inventory.json"
    require(inventory_path.is_file() and not inventory_path.is_symlink(), "async runtime inventory missing")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    require(set(inventory) == {"schema_version", "root", "files"}, "async runtime inventory fields")
    require(inventory.get("schema_version") == 1 and inventory.get("root") == "lancedb-async", "async runtime inventory identity")
    entries = inventory.get("files")
    require(isinstance(entries, list), "async runtime inventory entries")
    expected: dict[str, dict[str, Any]] = {}
    for entry in entries:
        require(set(entry) == {"path", "sha256", "size"}, "async runtime inventory entry fields")
        relative = entry.get("path")
        require(isinstance(relative, str) and relative not in expected, "async runtime inventory path")
        require(relative in {"worker-command.json", "async-connect-phases.jsonl"} or relative.startswith("local-lancedb/"), "unexpected async runtime artifact")
        expected[relative] = entry
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    require(actual == set(expected), "async runtime exact file inventory")
    require(not any(path.is_symlink() for path in root.rglob("*")), "async runtime symlink")
    for relative, entry in expected.items():
        path = root / relative
        require(path.stat().st_size == entry["size"] and sha(path) == entry["sha256"], f"async runtime drift: {relative}")
    framework_run = f"{run_id}-lancedb-async"
    validate_async_phases(root / "async-connect-phases.jsonl", trial_id=run_id, run_id=framework_run)
    command = json.loads((root / "worker-command.json").read_text(encoding="utf-8"))
    require(isinstance(command, list) and sum("gate2c_lancedb_async_diagnostic.py" in item for item in command) == 1, "async worker command")
    value = json.loads((evidence / "lancedb-async-diagnostic.json").read_text(encoding="utf-8"))
    validate_async_result(value, trial_id=run_id, run_id=framework_run)
    scan_evidence(root)


def validate_memory_async_runtime(repo: Path, evidence: Path, run_id: str) -> None:
    from gate2c_step02_rehearsal import validate_memory_async_phases, validate_memory_async_result

    root = repo / RUNTIME_ROOT / run_id / "lancedb-memory-async"
    require(root.is_dir() and not root.is_symlink(), f"in-memory diagnostic runtime missing: {run_id}")
    inventory_path = evidence / "runtime-inventory.json"
    require(inventory_path.is_file() and not inventory_path.is_symlink(), "in-memory runtime inventory missing")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    require(set(inventory) == {"schema_version", "root", "files"}, "in-memory runtime inventory fields")
    require(inventory.get("schema_version") == 1 and inventory.get("root") == "lancedb-memory-async", "in-memory runtime inventory identity")
    entries = inventory.get("files")
    require(isinstance(entries, list), "in-memory runtime inventory entries")
    expected: dict[str, dict[str, Any]] = {}
    for entry in entries:
        require(set(entry) == {"path", "sha256", "size"}, "in-memory runtime inventory entry fields")
        relative = entry.get("path")
        require(isinstance(relative, str) and relative not in expected, "in-memory runtime inventory path")
        require(relative in {"worker-command.json", "memory-async-connect-phases.jsonl"}, "unexpected in-memory runtime artifact")
        expected[relative] = entry
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    require(actual == set(expected), "in-memory runtime exact file inventory")
    require(not any(path.is_symlink() for path in root.rglob("*")), "in-memory runtime symlink")
    for relative, entry in expected.items():
        path = root / relative
        require(path.stat().st_size == entry["size"] and sha(path) == entry["sha256"], f"in-memory runtime drift: {relative}")
    framework_run = f"{run_id}-lancedb-memory-async"
    validate_memory_async_phases(root / "memory-async-connect-phases.jsonl", trial_id=run_id, run_id=framework_run)
    command = json.loads((root / "worker-command.json").read_text(encoding="utf-8"))
    require(isinstance(command, list) and sum("gate2c_lancedb_memory_async_diagnostic.py" in item for item in command) == 1, "in-memory worker command")
    value = json.loads((evidence / "lancedb-memory-async-diagnostic.json").read_text(encoding="utf-8"))
    validate_memory_async_result(value, trial_id=run_id, run_id=framework_run)
    scan_evidence(root)


def load_source_manifest(
    root: Path,
    expected_sources: set[str] | None = None,
) -> dict[str, str]:
    path = root / SOURCE_MANIFEST
    require(path.is_file(), "Step 2C.02 installed-source manifest missing")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "installed-source manifest digest")
        require(relative not in entries, f"duplicate installed-source manifest path: {relative}")
        entries[relative] = digest
    expected = INSTALLED_SOURCES if expected_sources is None else expected_sources
    require(set(entries) == expected, "installed-source manifest path inventory")
    return entries


def verify_installed_sources(
    root: Path,
    expected_sources: set[str] | None = None,
) -> None:
    verify_path_hashes(
        root,
        load_source_manifest(root, expected_sources),
        "installed Step 2C.02 source",
    )


def canonical_sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_source_epoch_values(
    authorization_source_sha: str,
    decision_source_sha: str,
    governance_predecessor_sha: str,
) -> None:
    """Keep immutable rehearsal authority distinct from later governance source."""
    require(
        authorization_source_sha == CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA,
        "historical corrected-environment authorization source epoch",
    )
    require(
        decision_source_sha == CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA,
        "human decision historical rehearsal source epoch",
    )
    require(
        governance_predecessor_sha == HUMAN_DECISION_GOVERNANCE_SOURCE_MANIFEST_SHA,
        "human-decision governance source epoch",
    )
    require(
        governance_predecessor_sha != authorization_source_sha,
        "historical rehearsal and current governance source epochs must remain distinct",
    )


def verify_checksum_manifest(root: Path, relative: str) -> None:
    """Verify a closed package checksum manifest without executing package code."""
    manifest = root / relative
    require(manifest.is_file() and not manifest.is_symlink(), f"package checksum manifest missing: {relative}")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, path_value = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"package checksum digest: {relative}")
        candidate = Path(path_value)
        require(not candidate.is_absolute() and ".." not in candidate.parts, f"unsafe package checksum path: {path_value}")
        path = root / candidate
        require(path.is_file() and not path.is_symlink(), f"package checksum path missing: {path_value}")
        require(sha(path) == digest, f"package checksum drift: {path_value}")


def validate_closed_package(root: Path, manifest: dict[str, Any]) -> None:
    """Verify the package's declared inventory and both internal checksum layers."""
    require(root.is_dir() and not root.is_symlink(), f"package missing: {root.name}")
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    require(actual == manifest.get("package_inventory"), f"closed package inventory drift: {root.name}")
    require(len(actual) == manifest.get("package_file_count"), f"package file count drift: {root.name}")
    require(not any(path.is_symlink() for path in root.rglob("*")), f"package symlink prohibited: {root.name}")
    verify_checksum_manifest(root, "payload-sha256.txt")
    verify_checksum_manifest(root, "package-sha256.txt")


def validate_human_decision_governance_transition(content: Path) -> Path:
    """Bind the historical rehearsal epoch to the exact governance-only v1 transition."""
    package = EXTERNAL_PACKAGE_ROOT / HUMAN_DECISION_PACKAGE
    require(package.is_dir() and not package.is_symlink(), "human-decision governance package missing")
    require(sha(package / "manifest.json") == HUMAN_DECISION_PACKAGE_MANIFEST_SHA, "human-decision package manifest drift")
    require(sha(package / "payload-sha256.txt") == HUMAN_DECISION_PACKAGE_PAYLOAD_MANIFEST_SHA, "human-decision payload checksum manifest drift")
    require(sha(package / "package-sha256.txt") == HUMAN_DECISION_PACKAGE_CHECKSUM_MANIFEST_SHA, "human-decision package checksum manifest drift")
    verify_checksum_manifest(package, "payload-sha256.txt")
    verify_checksum_manifest(package, "package-sha256.txt")
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    require(
        package_manifest.get("package") == "gate-2c-step02-crewai-recovery-architecture-human-decision"
        and package_manifest.get("version") == "1.0.0"
        and package_manifest.get("package_kind") == "GOVERNANCE_ONLY_HUMAN_ARCHITECTURE_DECISION",
        "human-decision governance package identity",
    )
    require(
        package_manifest.get("predecessor", {}).get("installed_source_manifest_sha256")
        == CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA,
        "human-decision package historical source predecessor",
    )
    package_payload = package / "payload"
    require(
        sha(package_payload / SOURCE_MANIFEST) == HUMAN_DECISION_GOVERNANCE_SOURCE_MANIFEST_SHA,
        "human-decision package governance source result",
    )
    require(sha(package_payload / DECISION_PATH) == HUMAN_DECISION_SHA, "human-decision package decision payload")
    require(sha(content / DECISION_PATH) == HUMAN_DECISION_SHA, "installed human-decision record drift")

    repair_package = EXTERNAL_PACKAGE_ROOT / HUMAN_DECISION_REPAIR_PACKAGE
    require(repair_package.is_dir() and not repair_package.is_symlink(), "human-decision repair package missing")
    require(sha(repair_package / "manifest.json") == HUMAN_DECISION_REPAIR_PACKAGE_MANIFEST_SHA, "human-decision repair manifest drift")
    require(sha(repair_package / "payload-sha256.txt") == HUMAN_DECISION_REPAIR_PACKAGE_PAYLOAD_MANIFEST_SHA, "human-decision repair payload checksum manifest drift")
    require(sha(repair_package / "package-sha256.txt") == HUMAN_DECISION_REPAIR_PACKAGE_CHECKSUM_MANIFEST_SHA, "human-decision repair package checksum manifest drift")
    verify_checksum_manifest(repair_package, "payload-sha256.txt")
    verify_checksum_manifest(repair_package, "package-sha256.txt")
    repair_manifest = json.loads((repair_package / "manifest.json").read_text(encoding="utf-8"))
    require(
        repair_manifest.get("package") == "gate-2c-step02-crewai-recovery-architecture-human-decision"
        and repair_manifest.get("version") == "1.0.2"
        and repair_manifest.get("package_kind") == "GOVERNANCE_ONLY_HUMAN_ARCHITECTURE_DECISION_INSTALLER_ONLY_SAME_BOUNDARY_REPAIR",
        "human-decision repair package identity",
    )
    repair_payload = repair_package / "payload"
    require(sha(repair_payload / SOURCE_MANIFEST) == HUMAN_DECISION_REPAIR_SOURCE_MANIFEST_SHA, "human-decision repair source result")
    require(sha(repair_payload / "scripts/gate2c_step02_audit.py") == HUMAN_DECISION_REPAIR_AUDIT_SHA, "human-decision repair audit source")
    verify_installed_sources(repair_payload, INSTALLED_SOURCES - INSTALL_CREATE - PROCESS_IDENTITY_INSTALL_CREATE - POST_SIGKILL_INSTALL_CREATE - POST_EXPIRY_PARTIAL_INSTALL_CREATE)

    repair_paths = {"scripts/gate2c_step02_audit.py", SOURCE_MANIFEST}
    installed_paths = (
        set(package_manifest["install"]["update"])
        | set(package_manifest["install"]["create"])
    )
    require(repair_paths <= installed_paths, "repair paths absent from human-decision governance transition")
    for relative in sorted(installed_paths - repair_paths):
        require(sha(repair_payload / relative) == sha(package_payload / relative), f"historical governance transition drift: {relative}")
    return repair_payload


def validate_drupal_reset_support_transition(
    repo: Path,
    content: Path,
    mode: str,
    *,
    synthetic_installed: bool = False,
    support_package: Path | None = None,
    predecessor_package: Path | None = None,
    candidate_repository_source: Path | None = None,
) -> None:
    """Keep the installed v1.0.1 support epoch bound as historical predecessor."""
    del repo, content, mode, synthetic_installed, candidate_repository_source
    package = support_package or EXTERNAL_PACKAGE_ROOT / DRUPAL_RESET_SUPPORT_PACKAGE
    predecessor = predecessor_package or EXTERNAL_PACKAGE_ROOT / HUMAN_DECISION_REPAIR_PACKAGE
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    validate_closed_package(package, package_manifest)
    require(
        package_manifest.get("package") == "gate-2c-step02-drupal-reset-model-free-proof"
        and package_manifest.get("version") == "1.0.1"
        and package_manifest.get("package_kind") == "MODEL_FREE_DRUPAL_PERSISTENT_LOCK_AND_RESET_PROOF_SUPPORT_SAME_BOUNDARY_REPAIR",
        "Drupal/reset support repair package identity",
    )
    require(
        package_manifest.get("predecessor", {}).get("installed_source_manifest_sha256")
        == HUMAN_DECISION_REPAIR_SOURCE_MANIFEST_SHA,
        "Drupal/reset support predecessor epoch",
    )
    install = package_manifest.get("install", {})
    require(tuple(install.get("update", [])) == DRUPAL_RESET_SUPPORT_UPDATE_PATHS, "Drupal/reset support update authority")
    require(install.get("create") == [] and install.get("delete") == [], "Drupal/reset support create/delete authority")

    payload = package / "payload"
    predecessor_payload = predecessor / "payload"
    require(sha(predecessor_payload / SOURCE_MANIFEST) == HUMAN_DECISION_REPAIR_SOURCE_MANIFEST_SHA, "predecessor source manifest epoch")
    historical_sources = INSTALLED_SOURCES - INSTALL_CREATE - PROCESS_IDENTITY_INSTALL_CREATE - POST_SIGKILL_INSTALL_CREATE - POST_EXPIRY_PARTIAL_INSTALL_CREATE
    verify_installed_sources(predecessor_payload, historical_sources)
    verify_installed_sources(payload, historical_sources)
    predecessor_sources = load_source_manifest(predecessor_payload, historical_sources)
    successor_sources = load_source_manifest(payload, historical_sources)
    require(set(predecessor_sources) == set(successor_sources) == historical_sources, "support transition source inventory")
    changed_sources = {
        relative for relative in historical_sources
        if predecessor_sources[relative] != successor_sources[relative]
    }
    require(
        changed_sources == set(DRUPAL_RESET_SUPPORT_UPDATE_PATHS) - {SOURCE_MANIFEST},
        f"support transition includes unauthorized or missing source changes: {sorted(changed_sources)}",
    )
    successor_manifest_sha = sha(payload / SOURCE_MANIFEST)
    require(
        package_manifest.get("successor", {}).get("installed_source_manifest_sha256") == successor_manifest_sha,
        "Drupal/reset support successor epoch",
    )
    for relative in DRUPAL_RESET_SUPPORT_UPDATE_PATHS:
        require((payload / relative).is_file() and not (payload / relative).is_symlink(), f"authorized successor path missing: {relative}")
    require(successor_manifest_sha == CURRENT_INSTALLED_SOURCE_MANIFEST_SHA, "installed v1.0.1 support epoch")


def validate_failed_start_repair_transition(
    repo: Path,
    content: Path,
    mode: str,
    *,
    synthetic_installed: bool = False,
) -> None:
    """Validate this exact failed-start repair from 851b9224... to its sealed successor."""
    require(mode in {"candidate", "installed"}, "unsupported repair transition mode")
    package = EXTERNAL_PACKAGE_ROOT / FAILED_START_REPAIR_PACKAGE
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    validate_closed_package(package, package_manifest)
    require(
        package_manifest.get("package") == "gate-2c-step02-drupal-failed-start-repair-and-replacement-admission"
        and package_manifest.get("version") == "1.0.0"
        and package_manifest.get("package_kind") == "DRUPAL_FAILED_START_REPAIR_AND_SINGLE_USE_REPLACEMENT_ADMISSION",
        "failed-start repair package identity",
    )
    predecessor = package_manifest.get("predecessor", {})
    require(predecessor.get("installed_source_manifest_sha256") == CURRENT_INSTALLED_SOURCE_MANIFEST_SHA, "failed-start repair predecessor source epoch")
    require(predecessor.get("permanent_audit_sha256") == "ee8aa46205906ecf74980078fc284a2c0e810664d187a24e30669d3948694113", "failed-start repair predecessor audit")
    install = package_manifest.get("install", {})
    require(set(install.get("update", [])) == INSTALL_UPDATE, "failed-start repair update authority")
    require(set(install.get("create", [])) == INSTALL_CREATE, "failed-start repair create authority")
    require(install.get("delete") == [], "failed-start repair delete authority")
    payload = package / "payload"
    verify_installed_sources(payload, INSTALLED_SOURCES - PROCESS_IDENTITY_INSTALL_CREATE - POST_SIGKILL_INSTALL_CREATE - POST_EXPIRY_PARTIAL_INSTALL_CREATE)
    require(sha(payload / SOURCE_MANIFEST) == package_manifest.get("successor", {}).get("installed_source_manifest_sha256"), "failed-start repair successor source epoch")
    # This package is historical. Its sealed payload proves its own transition; later
    # source epochs are validated by their distinct transition validators below.


def validate_process_identity_epoch_roles(
    mode: str,
    live_source_manifest_sha: str,
    successor_source_manifest_sha: str,
    *,
    synthetic_installed: bool = False,
) -> None:
    """Keep the consumed admission epoch historical while advancing live source."""
    require(mode in {"candidate", "installed"}, "unsupported process-identity repair mode")
    require(successor_source_manifest_sha != DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA, "process-identity successor must advance historical epoch")
    if mode == "candidate" or synthetic_installed:
        require(live_source_manifest_sha == DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA, "candidate/synthetic repository must retain historical predecessor epoch")
    else:
        require(live_source_manifest_sha == successor_source_manifest_sha, "installed process-identity successor epoch")


def validate_process_identity_repair_transition(repo: Path, content: Path, mode: str, *, synthetic_installed: bool = False) -> None:
    package = EXTERNAL_PACKAGE_ROOT / PROCESS_IDENTITY_REPAIR_PACKAGE
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    validate_closed_package(package, package_manifest)
    require(package_manifest.get("package") == "gate-2c-step02-drupal-process-identity-and-further-replacement-admission" and package_manifest.get("version") == "1.0.1", "process-identity repair package identity")
    require(package_manifest.get("predecessor", {}).get("installed_source_manifest_sha256") == DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA, "process-identity repair predecessor epoch")
    install = package_manifest.get("install", {})
    require(set(install.get("update", [])) == {
        "drupal/scripts/gate2c-step02-drupal-rehearsal.php", "scripts/gate2c_step02_audit.py",
        "scripts/gate2c_step02_rehearsal.py", "scripts/gate2c_step02_supervisor.py",
        "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh", SOURCE_MANIFEST,
    }, "process-identity repair update authority")
    require(set(install.get("create", [])) == {
        DRUPAL_FURTHER_REPLACEMENT_ADMISSION,
        "shared/contracts/GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.sha256",
        DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SCHEMA,
    } and install.get("delete") == [], "process-identity repair create/delete authority")
    payload = package / "payload"
    verify_installed_sources(payload, INSTALLED_SOURCES - POST_SIGKILL_INSTALL_CREATE - POST_EXPIRY_PARTIAL_INSTALL_CREATE)
    successor_sha = sha(payload / SOURCE_MANIFEST)
    require(successor_sha == package_manifest.get("successor", {}).get("installed_source_manifest_sha256"), "process-identity repair successor epoch")
    require(successor_sha == POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "process-identity installed epoch")
    # This sealed package is historical. Later transition validators bind the
    # live source epoch independently instead of forcing it back to 2d41065f....


def validate_post_sigkill_repair_transition(repo: Path, content: Path, mode: str, *, synthetic_installed: bool = False) -> None:
    """Bind the installed 2d41065f... epoch to this prospective-only repair."""
    package = EXTERNAL_PACKAGE_ROOT / POST_SIGKILL_REPAIR_PACKAGE
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    validate_closed_package(package, package_manifest)
    require(package_manifest.get("package") == "gate-2c-step02-drupal-post-sigkill-termination-and-missed-immediate-governance" and package_manifest.get("version") == "1.0.0", "post-SIGKILL repair package identity")
    require(package_manifest.get("predecessor", {}).get("installed_source_manifest_sha256") == POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-SIGKILL repair predecessor epoch")
    install = package_manifest.get("install", {})
    require(set(install.get("update", [])) == POST_SIGKILL_INSTALL_UPDATE, "post-SIGKILL repair update authority")
    require(set(install.get("create", [])) == POST_SIGKILL_INSTALL_CREATE and install.get("delete") == [], "post-SIGKILL repair create/delete authority")
    payload = package / "payload"
    successor_sha = sha(payload / SOURCE_MANIFEST)
    require(successor_sha == package_manifest.get("successor", {}).get("installed_source_manifest_sha256"), "post-SIGKILL repair successor epoch")
    require(successor_sha != POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-SIGKILL repair must advance source epoch")
    require(successor_sha == POST_EXPIRY_PARTIAL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-SIGKILL installed successor lineage")


def validate_post_expiry_partial_transition(repo: Path, content: Path, mode: str, *, synthetic_installed: bool = False) -> None:
    """Bind the installed 743a3986... epoch to the non-certifying amendment."""
    if mode == "candidate" or synthetic_installed:
        package = content.parent
    else:
        package = EXTERNAL_PACKAGE_ROOT / POST_EXPIRY_PARTIAL_PACKAGE
    package_manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    validate_closed_package(package, package_manifest)
    require(package_manifest.get("package") == "gate-2c-step02-drupal-post-expiry-partial-observation-contract" and package_manifest.get("version") == "1.0.0", "post-expiry partial package identity")
    require(package_manifest.get("predecessor", {}).get("installed_source_manifest_sha256") == POST_EXPIRY_PARTIAL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-expiry partial predecessor epoch")
    install = package_manifest.get("install", {})
    require(set(install.get("update", [])) == POST_EXPIRY_PARTIAL_INSTALL_UPDATE, "post-expiry partial update authority")
    require(set(install.get("create", [])) == POST_EXPIRY_PARTIAL_INSTALL_CREATE and install.get("delete") == [], "post-expiry partial create/delete authority")
    payload = package / "payload"
    successor_sha = sha(payload / SOURCE_MANIFEST)
    require(successor_sha == package_manifest.get("successor", {}).get("installed_source_manifest_sha256"), "post-expiry partial successor epoch")
    require(successor_sha != POST_EXPIRY_PARTIAL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-expiry partial source epoch must advance")
    live_sha = sha(repo / SOURCE_MANIFEST)
    if mode == "candidate" or synthetic_installed:
        require(live_sha == POST_EXPIRY_PARTIAL_PREDECESSOR_SOURCE_MANIFEST_SHA, "post-expiry partial candidate predecessor epoch")
        require(content.resolve() == payload.resolve(), "post-expiry partial candidate content must be sealed payload")
    else:
        require(live_sha == successor_sha and content.resolve() == repo.resolve(), "installed post-expiry partial successor epoch")
    verify_installed_sources(content)


def protected_state_fingerprint(repo: Path) -> tuple[int, str]:
    roots = (
        ".cache/gate2c-step02",
        "evidence/gates/gate-2c/model-free-rehearsal-authorizations",
        "evidence/gates/gate-2c/model-free-rehearsal-preservation",
        "evidence/gates/gate-2c/model-free-rehearsals",
        "crewai/.runtime",
        "evidence/gates/gate-2b",
    )
    fixed = (
        "crewai/agentic_harness_crewai/gate2c_recovery.py",
        "langchain/agentic_harness_langgraph/gate2c_recovery.py",
        "scripts/gate2c_step02_supervisor.py",
        "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
    )
    paths: set[Path] = set()
    for relative in roots:
        paths.update(path for path in (repo / relative).rglob("*") if path.is_file())
    paths.update(repo / relative for relative in fixed if relative not in HISTORICAL_PROTECTED_SOURCE_PATHS)
    paths.update(EXTERNAL_PACKAGE_ROOT.glob("gate-2c-step02-*-result-preservation-v1.0.0/preservation-manifest.json"))
    entries = [
        (str(path.resolve()), path.stat().st_size, sha(path))
        for path in sorted(paths, key=lambda value: str(value))
    ]
    predecessor_payload = EXTERNAL_PACKAGE_ROOT / HUMAN_DECISION_REPAIR_PACKAGE / "payload"
    for relative in sorted(HISTORICAL_PROTECTED_SOURCE_PATHS):
        historical = predecessor_payload / relative
        current = repo / relative
        require(historical.is_file() and current.is_file(), f"historical protected source missing: {relative}")
        entries.append((str(current.resolve()), historical.stat().st_size, sha(historical)))
    entries.sort(key=lambda value: value[0])
    digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
    return len(entries), digest


def latest_pointer_fingerprint(repo: Path) -> tuple[int, str]:
    entries = [
        (path.relative_to(repo).as_posix(), path.stat().st_size, sha(path))
        for path in sorted(repo.rglob("LATEST*")) if path.is_file()
    ]
    digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
    return len(entries), digest


def validate_protected_fingerprint_values(
    protected_count: int,
    protected_digest: str,
    latest_count: int,
    latest_digest: str,
) -> None:
    require(protected_count == 366 and protected_digest == PROTECTED_STATE_FINGERPRINT, "protected recovery/evidence state fingerprint")
    require(latest_count == 7 and latest_digest == LATEST_POINTER_FINGERPRINT, "seven-LATEST aggregate fingerprint")


def validate_protected_transition_state(repo: Path) -> None:
    protected_count, protected_digest = protected_state_fingerprint(repo)
    latest_count, latest_digest = latest_pointer_fingerprint(repo)
    validate_protected_fingerprint_values(protected_count, protected_digest, latest_count, latest_digest)


def directory_identities(root: Path) -> set[str]:
    if not root.exists():
        return set()
    require(root.is_dir() and not root.is_symlink(), f"invalid identity root: {root}")
    require(not any(path.is_symlink() for path in root.iterdir()), f"symlink in identity root: {root}")
    return {path.name for path in root.iterdir() if path.is_dir()}


def validate_inventory_entries(root: Path, entries: Any, label: str) -> dict[str, dict[str, Any]]:
    require(isinstance(entries, list), f"{label} inventory list")
    expected: dict[str, dict[str, Any]] = {}
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {"path", "size", "sha256"}, f"{label} inventory entry")
        relative = entry.get("path")
        require(isinstance(relative, str) and relative and relative not in expected, f"{label} inventory path")
        candidate = Path(relative)
        require(not candidate.is_absolute() and ".." not in candidate.parts, f"unsafe {label} inventory path")
        require(isinstance(entry.get("size"), int) and entry["size"] >= 0, f"{label} inventory size")
        require(re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256"))) is not None, f"{label} inventory digest")
        expected[relative] = entry
    return expected


def actual_inventory(root: Path) -> dict[str, dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), f"family root missing: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"family symlink prohibited: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            result[relative] = {"path": relative, "size": path.stat().st_size, "sha256": sha(path)}
    return result


def assert_zero_external_activity(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"model_generations", "provider_requests", "drupal_operations", "recommendation_writes", "source_mutations"}:
                require(item in {0, None}, f"new family nonzero prohibited activity: {key}")
            assert_zero_external_activity(item)
    elif isinstance(value, list):
        for item in value:
            assert_zero_external_activity(item)


def validate_admission_anchor(content: Path) -> None:
    anchor = content / ADMISSION_ANCHOR
    sidecar = content / ADMISSION_ANCHOR_SIDECAR
    require(anchor.is_file() and sha(anchor) == ADMISSION_ANCHOR_SHA, "one-run admission anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{ADMISSION_ANCHOR_SHA}  GATE2C-STEP02-ONE-RUN-ADMISSION.json", "one-run admission sidecar")
    value = json.loads(anchor.read_text(encoding="utf-8"))
    baseline = value.get("historical_baseline", {})
    admission = value.get("admission", {})
    finalization = value.get("finalization", {})
    require(value.get("status") == "EMPTY_SINGLE_USE_SLOT", "admission anchor status")
    require(value.get("predecessor_installed_source_manifest_sha256") == PREDECESSOR_SOURCE_MANIFEST_SHA, "admission predecessor manifest")
    require(baseline == {
        "family_count": 12,
        "evidence_file_count": 39,
        "original_runtime_artifact_count": 67,
        "post_inspection_runtime_artifact_count": 4,
        "physical_file_count": 110,
        "canonical_inventory_sha256": HISTORICAL_INVENTORY_SHA,
    }, "admission historical baseline")
    require(admission.get("maximum_new_identities") == 1 and admission.get("identity_reuse") == "PROHIBITED", "one-run admission policy")
    require(finalization.get("outcomes") == ["PASS", "FAIL", "TIMEOUT"], "finalization outcome policy")
    require(finalization.get("interrupted_finalization") == "INCOMPLETE_FAIL_CLOSED", "interrupted finalization policy")


def validate_replacement_admission_anchor(content: Path) -> None:
    anchor = content / REPLACEMENT_ADMISSION_ANCHOR
    sidecar = content / REPLACEMENT_ADMISSION_ANCHOR_SIDECAR
    schema = content / REPLACEMENT_ADMISSION_SCHEMA
    require(anchor.is_file() and sha(anchor) == REPLACEMENT_ADMISSION_ANCHOR_SHA, "replacement admission anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{REPLACEMENT_ADMISSION_ANCHOR_SHA}  GATE2C-STEP02-OFFLINE-REHEARSAL-REPLACEMENT-ADMISSION.json", "replacement admission sidecar")
    require(schema.is_file(), "replacement admission schema missing")
    value = json.loads(anchor.read_text(encoding="utf-8"))
    predecessor = value.get("predecessor", {})
    baseline = value.get("retained_baseline", {})
    diagnostic = value.get("supporting_diagnostic", {})
    admission = value.get("replacement_admission", {})
    acceptance = value.get("acceptance", {})
    unchanged = value.get("unchanged_implementation", {})
    require(value.get("status") == "EMPTY_SINGLE_USE_REPLACEMENT_SLOT", "replacement admission status")
    require(predecessor.get("installed_source_manifest_sha256") == V1_0_14_SOURCE_MANIFEST_SHA, "replacement v1.0.14 predecessor")
    require(predecessor.get("consumed_run_id") == LEGACY_CLASSIFICATION_RUN_ID, "replacement consumed identity")
    require(predecessor.get("consumed_authorization_sha256") == "c5827b91aae862dca52ecfc7b6618e0ef1e007404cc68c029da5929a7a8ecfb3", "replacement consumed authorization")
    require(predecessor.get("finalized_fail_sha256") == LEGACY_CLASSIFICATION_FINALIZATION_SHA and predecessor.get("outcome") == "FAIL", "replacement finalized FAIL binding")
    require(predecessor.get("failed_attempt_sha256") == LEGACY_CLASSIFICATION_FAILURE_SHA, "replacement failed-attempt binding")
    require(predecessor.get("crewai_supervisor_diagnostic_sha256") == LEGACY_CLASSIFICATION_DIAGNOSTIC_SHA, "replacement supervisor diagnostic binding")
    require(baseline == {
        "family_count": 13,
        "rehearsal_evidence_file_count": 44,
        "runtime_file_count": 83,
        "authorization_record_count": 1,
        "finalization_record_count": 1,
        "physical_file_count": 129,
        "canonical_inventory_sha256": RETAINED_BASELINE_INVENTORY_SHA,
    }, "replacement retained baseline")
    require(diagnostic.get("result_manifest_sha256") == "6670110a91f05f4b8bec97d73c1be47b9072a96eeebe499ddedd23f883fbfba9", "supporting diagnostic result binding")
    require(diagnostic.get("package_role") == "NON_PREDECESSOR_PROVENANCE_CONTEXT" and diagnostic.get("package_closed_world_status") == "FAIL_UNDECLARED_PYTHON_CACHE", "contaminated diagnostic package classification")
    require(diagnostic.get("undeclared_cache_sha256") == "80140dcc64cb91c4fca7b914c63d91b863b5399754531833231e5419ccda0419", "diagnostic cache provenance binding")
    require(admission.get("maximum_new_identities") == 1 and admission.get("consumed_admission_reopened") is False, "replacement single-use policy")
    require(admission.get("historical_identity_reuse") == "PROHIBITED" and admission.get("automatic_replacement_or_retry") == "PROHIBITED" and admission.get("additional_replacement_identities") == 0, "replacement no-retry policy")
    require(all(acceptance.get(key) is True for key in (
        "complete_langgraph_and_crewai_family_required",
        "independently_verified_target_6_seam_required",
        "experimental_worker_termination_required",
        "public_recovery_interfaces_required",
        "target_7_first_required",
        "zero_replay_required",
        "zero_duplicates_required",
        "failure_or_timeout_must_be_finalized_and_retained",
    )), "replacement acceptance requirements")
    require(acceptance.get("automatic_replacement_after_failure_or_timeout") is False, "replacement failure retention policy")
    require(all(unchanged.get(key) is True for key in (
        "worker_adapters", "supervisor", "persistence", "recovery", "timeouts",
        "failure_injection", "experiment_controls", "validator", "frozen_contracts",
    )), "unchanged execution implementation")
    require(unchanged.get("future_cleanup_classification") == "V1_0_14_CORRECTED_SOURCE_BOUND_POLICY", "corrected future cleanup classification")


def validate_corrected_environment_preflight(value: dict[str, Any]) -> None:
    required = {
        "status": "CORRECTED_EXECUTION_ENVIRONMENT_PREFLIGHT_PASS",
        "python_version": "3.12.13",
        "no_new_privs": 0,
        "seccomp": 0,
        "event_loop_policy": "_UnixDefaultEventLoopPolicy",
        "selector": "EpollSelector",
        "auxiliary_python_threads_constructed": 1,
        "auxiliary_thread_start_calls": 1,
        "auxiliary_worker_function_started": 1,
        "auxiliary_worker_function_completed": 1,
        "auxiliary_thread_alive_after_join": False,
        "call_soon_threadsafe_calls": 1,
        "callback_calls": 1,
        "callback_executed": True,
        "event_await_resumed": True,
        "socketpair_bytes_sent": 1,
        "socketpair_bytes_received": 1,
        "socketpair_one_null_byte_round_trip": True,
        "crewai_imported": False,
    }
    require(isinstance(value, dict) and all(value.get(key) == expected for key, expected in required.items()), "corrected-environment preflight binding")
    require(value.get("failed_checks") == [], "corrected-environment preflight failures")


def validate_corrected_environment_evidence() -> None:
    for directory, expected in DIAGNOSTIC_PRESERVATIONS.items():
        manifest = EXTERNAL_PACKAGE_ROOT / directory / "preservation-manifest.json"
        require(manifest.is_file() and sha(manifest) == expected, f"diagnostic preservation drift: {directory}")
    invalid = json.loads((EXTERNAL_PACKAGE_ROOT / "gate-2c-step02-crewai-corrected-environment-representative-startup-verification-v1.0.0-result-preservation-v1.0.0/preservation-manifest.json").read_text(encoding="utf-8"))
    require(invalid.get("classification") == "INVALID_EXECUTION_ENVIRONMENT_PREFLIGHT" and invalid.get("representative_worker_launched") is False and invalid.get("public_kickoff_calls") == 0, "v1.0.0 invalid-preflight history")
    root = EXTERNAL_PACKAGE_ROOT / "gate-2c-step02-crewai-corrected-environment-representative-startup-verification-v1.0.1-result-preservation-v1.0.0"
    manifest = json.loads((root / "preservation-manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("execution_identity") == CORRECTED_STARTUP_EXECUTION_ID and manifest.get("classification") == "PASS_CORRECTED_ENVIRONMENT_REPRESENTATIVE_STARTUP", "corrected startup preservation identity/classification")
    require(manifest.get("public_kickoff_calls") == 1 and manifest.get("worker_returncode") == -15 and manifest.get("cleanup_signal") == 15, "corrected startup kickoff/cleanup")
    preflight = json.loads((root / "workspace/preflight-result.json").read_text(encoding="utf-8"))
    validate_corrected_environment_preflight(preflight)
    result = json.loads((root / "workspace/verification-result.json").read_text(encoding="utf-8"))
    require(result.get("status") == "PASS_CORRECTED_ENVIRONMENT_REPRESENTATIVE_STARTUP" and result.get("verification_id") == CORRECTED_STARTUP_EXECUTION_ID, "corrected startup result")
    require(result.get("public_kickoff_calls") == 1 and result.get("first_reporter_observation") is True and result.get("reporter_write_completed") is True and result.get("expected_sentinel_activated") is True, "corrected startup reporter/sentinel proof")
    require(result.get("target_processing_boundary_crossed") is False and result.get("disposable_database_zero_operation_counts") == {"flow_state_rows": 0, "pending_feedback_rows": 0}, "corrected startup zero target/persistence")
    require(result.get("continuous_python_tracing") is False and result.get("trace_specific_preimports") is False, "corrected startup trace/import boundary")
    phases = (root / "workspace/.cache/gate2c-step02" / CORRECTED_STARTUP_EXECUTION_ID / "control/startup-phases.jsonl").read_text(encoding="utf-8").splitlines()
    require([json.loads(line)["phase"] for line in phases] == ["flow_invocation_started", "flow_method_started"], "corrected startup durable phase sequence")


def validate_corrected_admission_anchor(content: Path) -> None:
    anchor = content / CORRECTED_ADMISSION_ANCHOR
    sidecar = content / CORRECTED_ADMISSION_ANCHOR_SIDECAR
    require(anchor.is_file() and sha(anchor) == CORRECTED_ADMISSION_ANCHOR_SHA, "corrected-environment admission anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{CORRECTED_ADMISSION_ANCHOR_SHA}  GATE2C-STEP02-CORRECTED-ENVIRONMENT-OFFLINE-REHEARSAL-ADMISSION.json", "corrected-environment admission sidecar")
    value = json.loads(anchor.read_text(encoding="utf-8"))
    require(value.get("status") == "EMPTY_SINGLE_USE_CORRECTED_ENVIRONMENT_SLOT", "corrected-environment admission status")
    historical = value.get("historical_results", {})
    require(historical.get("immutable") is True, "historical immutability")
    require(historical.get("first_governed_fail", {}).get("finalization_sha256") == LEGACY_CLASSIFICATION_FINALIZATION_SHA, "first FAIL binding")
    require(historical.get("replacement_fail", {}).get("finalization_sha256") == REPLACEMENT_FAIL_FINALIZATION_SHA, "replacement FAIL binding")
    evidence = value.get("corrected_environment_evidence", {})
    require(evidence.get("execution_identity") == CORRECTED_STARTUP_EXECUTION_ID and evidence.get("preservation_manifest_sha256") == CORRECTED_STARTUP_PRESERVATION_SHA, "corrected startup contract binding")
    admission = value.get("admission", {})
    require(admission.get("maximum_new_identities") == 1 and admission.get("historical_identity_reuse") == "PROHIBITED", "corrected admission single-use")
    require(admission.get("automatic_replacement_or_retry") == "PROHIBITED" and admission.get("additional_identities_from_any_outcome") == 0, "corrected admission no retry/replacement")
    require(admission.get("preflight_must_pass_before_identity_allocation") is True and admission.get("fresh_preflight_must_pass_before_execution") is True, "corrected preflight governance")
    decision = value.get("human_decision_boundary", {})
    require(decision.get("pass_status") == "APPROVAL_READY" and all(decision.get(key) is False for key in decision if key != "pass_status"), "human decision boundary")


def validate_drupal_replacement_admission_anchor(content: Path) -> None:
    anchor = content / DRUPAL_REPLACEMENT_ADMISSION_ANCHOR
    sidecar = content / DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SIDECAR
    schema_path = content / DRUPAL_REPLACEMENT_ADMISSION_SCHEMA
    require(anchor.is_file() and sha(anchor) == DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA, "Drupal replacement admission anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA}  GATE2C-STEP02-DRUPAL-REPLACEMENT-ADMISSION.json", "Drupal replacement admission sidecar")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    value = json.loads(anchor.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    failed = value.get("failed_attempt", {})
    require(failed.get("run_id") == FAILED_DRUPAL_RUN_ID and failed.get("status") == "FAILED_PRESERVED", "Drupal replacement failed identity")
    require(failed.get("start_authorization") == "CONSUMED" and failed.get("aggregate_sha256") == FAILED_DRUPAL_FAMILY_AGGREGATE_SHA, "Drupal replacement failed-family governance")
    expected_paths = {
        f"{REHEARSAL_EVIDENCE_ROOT}/{FAILED_DRUPAL_RUN_ID}/{relative}": digest
        for relative, digest in FAILED_DRUPAL_EVIDENCE.items()
    } | {
        f"drupal/.cache/gate2c-step02/{FAILED_DRUPAL_RUN_ID}/{relative}": digest
        for relative, digest in FAILED_DRUPAL_RUNTIME.items()
    }
    artifacts = failed.get("artifacts")
    require(isinstance(artifacts, list) and len(artifacts) == 6, "Drupal replacement failed-family artifact count")
    require({item.get("path"): item.get("sha256") for item in artifacts} == expected_paths, "Drupal replacement failed-family hash bindings")
    admission = value.get("replacement_admission", {})
    require(value.get("status") == "EMPTY_SINGLE_USE_DRUPAL_REPLACEMENT_SLOT", "Drupal replacement slot status")
    require(value.get("replacement_reason") == "SOURCE_RUNTIME_INSTRUMENTATION_DEFECT", "Drupal replacement reason")
    require(admission.get("identity_allocation") == "DEFERRED_UNTIL_SEPARATE_HUMAN_AUTHORIZATION", "Drupal replacement identity must remain deferred")
    require(admission.get("maximum_new_identities") == 1 and admission.get("additional_replacement_identities") == 0, "Drupal replacement single-use policy")
    require(admission.get("failed_identity_reuse") == "PROHIBITED" and admission.get("automatic_retry") == "PROHIBITED", "Drupal replacement retry policy")
    require(admission.get("consumed_original_start_token_carry_forward") == "PROHIBITED", "Drupal consumed start token policy")
    require(admission.get("replacement_start_requires_separate_human_authorization") is True, "Drupal replacement start authorization boundary")


def validate_failed_drupal_family(repo: Path) -> set[str]:
    evidence = repo / REHEARSAL_EVIDENCE_ROOT / FAILED_DRUPAL_RUN_ID
    runtime = repo / "drupal/.cache/gate2c-step02" / FAILED_DRUPAL_RUN_ID
    require(evidence.is_dir() and runtime.is_dir(), "immutable failed Drupal family missing")
    require(not any(path.is_symlink() for path in (*evidence.rglob("*"), *runtime.rglob("*"))), "failed Drupal family symlink")
    evidence_inventory = {path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()}
    runtime_inventory = {path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file()}
    require(evidence_inventory == set(FAILED_DRUPAL_EVIDENCE), "failed Drupal evidence inventory")
    require(runtime_inventory == set(FAILED_DRUPAL_RUNTIME), "failed Drupal runtime inventory")
    verify_path_hashes(evidence, FAILED_DRUPAL_EVIDENCE, "failed Drupal evidence")
    verify_path_hashes(runtime, FAILED_DRUPAL_RUNTIME, "failed Drupal runtime")
    failed = json.loads((evidence / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == FAILED_DRUPAL_RUN_ID, "failed Drupal status")
    require(ledger.get("run_id") == FAILED_DRUPAL_RUN_ID and ledger.get("phases", [None])[0].get("status") == "CONSUMED", "failed Drupal start authorization")
    require(not (evidence / "evidence-manifest.json").exists() and not (evidence / "drupal-termination.json").exists(), "failed Drupal family cannot satisfy passing proof")
    scan_evidence(evidence)
    return {
        path.relative_to(repo).as_posix()
        for root in (evidence, runtime)
        for path in root.rglob("*") if path.is_file()
    }


def validate_failed_drupal_replacement_family(repo: Path) -> set[str]:
    evidence = repo / REHEARSAL_EVIDENCE_ROOT / FAILED_DRUPAL_REPLACEMENT_RUN_ID
    runtime = repo / "drupal/.cache/gate2c-step02" / FAILED_DRUPAL_REPLACEMENT_RUN_ID
    require(evidence.is_dir() and runtime.is_dir(), "immutable failed Drupal replacement family missing")
    require(not any(path.is_symlink() for path in (*evidence.rglob("*"), *runtime.rglob("*"))), "failed Drupal replacement family symlink")
    require({path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()} == set(FAILED_DRUPAL_REPLACEMENT_EVIDENCE), "failed Drupal replacement evidence inventory")
    require({path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file()} == set(FAILED_DRUPAL_REPLACEMENT_RUNTIME), "failed Drupal replacement runtime inventory")
    verify_path_hashes(evidence, FAILED_DRUPAL_REPLACEMENT_EVIDENCE, "failed Drupal replacement evidence")
    verify_path_hashes(runtime, FAILED_DRUPAL_REPLACEMENT_RUNTIME, "failed Drupal replacement runtime")
    inventory = []
    for root in (evidence, runtime):
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            inventory.append({"path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": sha(path)})
    require(canonical_sha(inventory) == FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA, "failed Drupal replacement aggregate")
    failed = json.loads((evidence / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    diagnostic = json.loads((evidence / "drupal-pre-seam-diagnostic.json").read_text(encoding="utf-8"))
    midpoint = json.loads((runtime / "control/midpoint.json").read_text(encoding="utf-8"))
    seam = json.loads((runtime / "control/seam-ready.json").read_text(encoding="utf-8"))
    require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == FAILED_DRUPAL_REPLACEMENT_RUN_ID, "failed Drupal replacement status")
    require(failed.get("drupal_pre_seam_diagnostic_sha256") == FAILED_DRUPAL_REPLACEMENT_EVIDENCE["drupal-pre-seam-diagnostic.json"], "failed Drupal replacement diagnostic binding")
    require(ledger.get("phases", [None])[0].get("status") == "CONSUMED", "failed Drupal replacement start authorization consumed")
    require(diagnostic.get("failure_reason") == "supervisor_validation_failure" and diagnostic.get("experimental_sigkill_delivered") is False, "failed Drupal replacement process-verification classification")
    require(diagnostic.get("automatic_retry_count") == 0 and diagnostic.get("midpoint_existed") is True and diagnostic.get("seam_ready_existed") is True, "failed Drupal replacement seam/no-retry facts")
    require(midpoint.get("completed_sequences") == [1, 2, 3, 4, 5, 6] and midpoint.get("next_target") == 7 and midpoint.get("target_7_started") is False, "failed Drupal replacement midpoint facts")
    require(seam.get("midpoint_sha256") == FAILED_DRUPAL_REPLACEMENT_RUNTIME["control/midpoint.json"], "failed Drupal replacement seam midpoint binding")
    require(seam.get("actual_worker_pid") == 14297 and seam.get("host_worker_pid") == 116003, "failed Drupal replacement PID binding")
    require(seam.get("lock_name_sha256") == "93f9fb0d6bb771ea02af01e25882731089e05776c73a18a98799ff1ce7a05527", "failed Drupal replacement lock identity")
    require(not (evidence / "drupal-termination.json").exists() and not (evidence / "evidence-manifest.json").exists(), "failed Drupal replacement cannot satisfy passing proof")
    authorization = repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT / FAILED_DRUPAL_REPLACEMENT_RUN_ID / "authorization.json"
    require(sha(authorization) == FAILED_DRUPAL_REPLACEMENT_ADMISSION_SHA, "failed Drupal replacement authorization drift")
    scan_evidence(evidence)
    return {path.relative_to(repo).as_posix() for root in (evidence, runtime) for path in root.rglob("*") if path.is_file()}


def validate_final_failed_drupal_family(repo: Path) -> set[str]:
    """Audit the immutable final run without manufacturing missing termination evidence."""
    evidence = repo / REHEARSAL_EVIDENCE_ROOT / FINAL_FAILED_DRUPAL_RUN_ID
    runtime = repo / "drupal/.cache/gate2c-step02" / FINAL_FAILED_DRUPAL_RUN_ID
    require(evidence.is_dir() and runtime.is_dir(), "immutable final failed Drupal family missing")
    require(not any(path.is_symlink() for path in (*evidence.rglob("*"), *runtime.rglob("*"))), "final failed Drupal family symlink")
    require({path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()} == set(FINAL_FAILED_DRUPAL_EVIDENCE), "final failed Drupal evidence inventory")
    require({path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file()} == set(FINAL_FAILED_DRUPAL_RUNTIME), "final failed Drupal runtime inventory")
    verify_path_hashes(evidence, FINAL_FAILED_DRUPAL_EVIDENCE, "final failed Drupal evidence")
    verify_path_hashes(runtime, FINAL_FAILED_DRUPAL_RUNTIME, "final failed Drupal runtime")
    inventory = []
    for root in (evidence, runtime):
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            inventory.append({"path": path.relative_to(repo).as_posix(), "size": path.stat().st_size, "sha256": sha(path)})
    require(canonical_sha(inventory) == FINAL_FAILED_DRUPAL_AGGREGATE_SHA, "final failed Drupal aggregate")
    failed = json.loads((evidence / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    midpoint = json.loads((runtime / "control/midpoint.json").read_text(encoding="utf-8"))
    seam = json.loads((runtime / "control/seam-ready.json").read_text(encoding="utf-8"))
    scan = json.loads((evidence / "drupal-pre-kill-process-scan.json").read_text(encoding="utf-8"))
    require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == FINAL_FAILED_DRUPAL_RUN_ID, "final failed Drupal status")
    require(failed.get("diagnostic", {}).get("experimental_sigkill_delivered") is False, "historical outer signal default must remain false")
    require(failed.get("diagnostic", {}).get("returncode") == 1 and "worker termination was not signal 9: 1" in failed.get("diagnostic", {}).get("sanitized_stderr", ""), "historical wrapper-return failure")
    require(failed.get("drupal_pre_kill_process_scan_sha256") == FINAL_FAILED_DRUPAL_EVIDENCE["drupal-pre-kill-process-scan.json"], "final failed pre-kill binding")
    require([item.get("status") for item in ledger.get("phases", [])] == ["CONSUMED", "PENDING", "PENDING"], "final failed lifecycle ledger")
    require(ledger.get("replacement_authorization_sha256") == FINAL_FAILED_DRUPAL_ADMISSION_SHA, "final failed admission binding")
    require(ledger.get("repaired_installed_source_manifest_sha256") == POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "final failed execution epoch")
    require(midpoint.get("completed_sequences") == [1, 2, 3, 4, 5, 6] and midpoint.get("next_target") == 7 and midpoint.get("target_7_started") is False, "final failed midpoint")
    require(seam.get("midpoint_sha256") == FINAL_FAILED_DRUPAL_RUNTIME["control/midpoint.json"] and seam.get("actual_worker_pid") == 28942 and seam.get("host_worker_pid") == 234677, "final failed seam binding")
    require(scan.get("decision") == "EXACT_SINGLETON_VERIFIED" and scan.get("matching_worker_pids") == [28942], "final failed exact pre-kill singleton")
    require(not any((evidence / name).exists() for name in ("drupal-signal-dispatch.json", "drupal-post-kill-process-scan.json", "drupal-termination.json", "drupal-immediate.json", "drupal-post-expiry.json", "evidence-manifest.json")), "final failed family gained fabricated lifecycle proof")
    authorization = repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT / FINAL_FAILED_DRUPAL_RUN_ID / "authorization.json"
    require(authorization.is_file() and sha(authorization) == FINAL_FAILED_DRUPAL_ADMISSION_SHA, "final failed authorization drift")
    scan_evidence(evidence)
    return {path.relative_to(repo).as_posix() for root in (evidence, runtime) for path in root.rglob("*") if path.is_file()}


def validate_final_failed_governance(content: Path) -> None:
    anchor = content / FINAL_FAILED_GOVERNANCE
    sidecar = content / FINAL_FAILED_GOVERNANCE_SIDECAR
    schema_path = content / FINAL_FAILED_GOVERNANCE_SCHEMA
    require(anchor.is_file() and sha(anchor) == FINAL_FAILED_GOVERNANCE_SHA, "final failed governance anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{FINAL_FAILED_GOVERNANCE_SHA}  GATE2C-STEP02-DRUPAL-FINAL-FAILED-ATTEMPT-GOVERNANCE.json", "final failed governance sidecar")
    value = json.loads(anchor.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(value)
    require(value.get("canonical_family_aggregate_sha256") == FINAL_FAILED_DRUPAL_AGGREGATE_SHA, "final failed governance aggregate")
    require(value.get("admission_sha256") == FINAL_FAILED_DRUPAL_ADMISSION_SHA and value.get("installed_source_epoch_at_execution") == POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "final failed governance lineage")
    require(value.get("worker_launch_count") == 1 and value.get("automatic_retry_count") == 0 and value.get("additional_worker_identities_permitted") == 0, "final failed no-more-workers policy")
    signal_boundary = value.get("signal_boundary", {})
    require(signal_boundary.get("pre_kill_decision") == "EXACT_SINGLETON_VERIFIED" and signal_boundary.get("kill_command_returncode") == 0 and signal_boundary.get("outer_wrapper_returncode") == 1, "final failed signal/wrapper distinction")
    require(signal_boundary.get("drupal_termination_artifact_present") is False and signal_boundary.get("post_kill_process_scan_artifact_present") is False, "final failed missing-proof classification")
    conflict = value.get("historical_provenance_conflict", {})
    require(conflict.get("outer_failed_attempt_experimental_sigkill_delivered") is False and conflict.get("historical_artifacts_must_not_be_rewritten") is True and conflict.get("termination_pass_certified") is False, "final failed provenance conflict")
    missed = value.get("missed_immediate_observation", {})
    require(missed.get("classification") == "IMMEDIATE_OBSERVATION_MISSED_DUE_TO_TERMINATION_PROOF_GATE" and missed.get("window_open_at_decision") is True, "missed immediate chronology")
    require(missed.get("command_invoked") is False and missed.get("lock_denial_proven") is False and missed.get("satisfies_immediate_pass") is False, "missed immediate must not pass")
    post = value.get("post_expiry_policy", {})
    require(post.get("current_source_admits_post_expiry") is False and post.get("partial_evidence_may_be_scientifically_useful") is True, "post-expiry partial-evidence policy")
    require(post.get("requires_separate_contract_amendment_and_human_authorization") is True and post.get("can_satisfy_current_step_2c02_certification") is False, "post-expiry certification boundary")


def validate_post_expiry_partial_contract(content: Path) -> dict[str, Any]:
    anchor = content / POST_EXPIRY_PARTIAL_CONTRACT
    sidecar = content / POST_EXPIRY_PARTIAL_CONTRACT_SIDECAR
    schema_path = content / POST_EXPIRY_PARTIAL_SCHEMA
    require(anchor.is_file() and sha(anchor) == POST_EXPIRY_PARTIAL_CONTRACT_SHA, "post-expiry partial contract drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{POST_EXPIRY_PARTIAL_CONTRACT_SHA}  GATE2C-STEP02-DRUPAL-POST-EXPIRY-PARTIAL-OBSERVATION-CONTRACT.json", "post-expiry partial sidecar")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    value = json.loads(anchor.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    require(value.get("status") == "ADMITTED_NOT_EXECUTED" and value.get("run_id") == FINAL_FAILED_DRUPAL_RUN_ID, "post-expiry partial exact identity")
    require(value.get("final_admission_sha256") == FINAL_FAILED_DRUPAL_ADMISSION_SHA, "post-expiry partial admission binding")
    require(value.get("final_failed_family_aggregate_sha256") == FINAL_FAILED_DRUPAL_AGGREGATE_SHA, "post-expiry partial final-family binding")
    require(value.get("prior_failed_family_aggregates") == [FAILED_DRUPAL_FAMILY_AGGREGATE_SHA, FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA], "post-expiry partial prior-family bindings")
    chronology = value.get("recorded_chronology", {})
    require(chronology.get("wall_clock_expiry_elapsed_is_evidence") is False and chronology.get("actual_observation_timestamp_required") is True, "elapsed time is not observation evidence")
    gaps = value.get("historical_gaps", {})
    require(gaps.get("immediate_lock_denial_proven") is False and gaps.get("immediate_observation_reconstructable") is False and gaps.get("continuous_lock_retention_until_expiry_proven") is False, "historical evidence gaps")
    mechanics = value.get("observation_mechanics", {})
    require(mechanics.get("worker_launch_count") == 0 and mechanics.get("target_processing_count") == 0 and mechanics.get("keyvalue_state_write_count") == 0, "partial observation operation boundary")
    require(mechanics.get("lock_probe_method") == "PERSISTENT_LOCK_ACQUIRE_THEN_IMMEDIATE_RELEASE" and mechanics.get("lock_probe_lease_seconds") == 1, "partial observation bounded lock probe")
    execution = value.get("execution_boundary", {})
    require(execution.get("maximum_observation_invocations") == 1 and execution.get("execution_authorized_by_contract") is False and execution.get("new_run_identity_permitted") is False, "partial observation separate authorization")
    guardrails = value.get("certification_guardrails", {})
    require(guardrails.get("certifying_evidence") is False and guardrails.get("step_2c02_status") == "UNCERTIFIED" and guardrails.get("reset_status") == "BLOCKED_REQUIRES_FULL_PASSING_DRUPAL_REHEARSAL", "partial observation certification/reset guardrails")
    workers = value.get("no_more_workers", {})
    require(workers.get("additional_worker_identities_permitted") == 0 and workers.get("replacement_slots_permitted") == 0 and workers.get("worker_retry_permitted") is False and workers.get("automatic_retry_permitted") is False, "no-more-worker policy")
    return value


def validate_post_expiry_partial_state(repo: Path, content: Path) -> tuple[set[str], str]:
    contract = validate_post_expiry_partial_contract(content)
    root = repo / POST_EXPIRY_PARTIAL_EVIDENCE_ROOT
    if not root.exists():
        return set(), "DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_ADMITTED_NOT_PERFORMED"
    require(root.is_dir() and not root.is_symlink(), "post-expiry partial evidence root")
    identities = {path.name for path in root.iterdir() if path.is_dir()}
    require(identities == {FINAL_FAILED_DRUPAL_RUN_ID}, "post-expiry partial exact identity count")
    identity_root = root / FINAL_FAILED_DRUPAL_RUN_ID
    require({path.name for path in identity_root.iterdir() if path.is_file()} == {"observation.json"}, "post-expiry partial evidence inventory")
    observation_path = identity_root / "observation.json"
    value = json.loads(observation_path.read_text(encoding="utf-8"))
    schema = json.loads((content / POST_EXPIRY_PARTIAL_SCHEMA).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(value)
    require(value.get("contract_sha256") == POST_EXPIRY_PARTIAL_CONTRACT_SHA, "post-expiry partial evidence contract binding")
    require(value.get("final_failed_family_aggregate_sha256") == FINAL_FAILED_DRUPAL_AGGREGATE_SHA and value.get("final_admission_sha256") == FINAL_FAILED_DRUPAL_ADMISSION_SHA, "post-expiry partial evidence historical binding")
    require(value.get("prior_failed_family_aggregates") == contract.get("prior_failed_family_aggregates"), "post-expiry partial prior-family evidence binding")
    require(value.get("installed_source_manifest_sha256") == sha(content / SOURCE_MANIFEST), "post-expiry partial evidence source epoch")
    require(value.get("observation_timestamp_unix", 0) >= contract["recorded_chronology"]["lock_expires_not_before_unix"], "post-expiry partial chronology")
    require(value.get("certifying_evidence") is False and value.get("immediate_lock_denial_reconstructed") is False and value.get("historical_termination_proof_reconstructed") is False, "post-expiry partial non-certifying evidence")
    scan_evidence(identity_root)
    return {observation_path.relative_to(repo).as_posix()}, "DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_PERFORMED_NON_CERTIFYING"


def validate_drupal_further_replacement_admission_anchor(content: Path) -> None:
    anchor = content / DRUPAL_FURTHER_REPLACEMENT_ADMISSION
    sidecar = anchor.with_suffix(".sha256")
    schema_path = content / DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SCHEMA
    require(anchor.is_file() and sha(anchor) == DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SHA, "Drupal further replacement admission anchor drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SHA}  GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.json", "Drupal further replacement sidecar")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    value = json.loads(anchor.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    require(value.get("predecessor_installed_source_manifest_sha256") == DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA, "Drupal further replacement predecessor epoch")
    validate_future_repaired_source_epoch(value.get("future_repaired_source_epoch"))
    failed = value.get("failed_replacement_attempt", {})
    require(failed.get("aggregate_sha256") == FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA and failed.get("admission_record_sha256") == FAILED_DRUPAL_REPLACEMENT_ADMISSION_SHA, "Drupal further replacement failed-family bindings")
    require(failed.get("experimental_sigkill_delivered") is False and failed.get("automatic_retry_count") == 0, "Drupal further replacement failed outcome")
    expected_artifacts = {
        **{f"{REHEARSAL_EVIDENCE_ROOT}/{FAILED_DRUPAL_REPLACEMENT_RUN_ID}/{path}": digest for path, digest in FAILED_DRUPAL_REPLACEMENT_EVIDENCE.items()},
        **{f"drupal/.cache/gate2c-step02/{FAILED_DRUPAL_REPLACEMENT_RUN_ID}/{path}": digest for path, digest in FAILED_DRUPAL_REPLACEMENT_RUNTIME.items()},
    }
    require({item.get("path"): item.get("sha256") for item in failed.get("artifacts", [])} == expected_artifacts, "Drupal further replacement inventory binding")
    admission = value.get("further_replacement_admission", {})
    require(admission.get("identity_allocation") == "DEFERRED_UNTIL_SEPARATE_HUMAN_AUTHORIZATION" and admission.get("maximum_new_identities") == 1, "Drupal further replacement allocation boundary")
    require(admission.get("automatic_retry") is False and admission.get("additional_replacements_after_this_slot") == 0, "Drupal further replacement no-retry policy")
    require(admission.get("execution_authorized") is False and admission.get("allocation_requires_separate_human_authorization") is True and admission.get("execution_requires_separate_human_authorization") is True, "Drupal further replacement human boundaries")


def validate_future_repaired_source_epoch(value: Any) -> None:
    """Require future allocation to bind the then-current manifest, never a fixed old epoch."""
    require(isinstance(value, dict), "Drupal further replacement future epoch rule")
    require(set(value) == {
        "manifest_path",
        "allocation_record_must_bind_current_manifest_sha256",
        "execution_must_match_allocated_manifest_sha256",
    }, "Drupal further replacement future epoch rule fields")
    require(value.get("manifest_path") == SOURCE_MANIFEST, "Drupal further replacement current-manifest path")
    require(value.get("allocation_record_must_bind_current_manifest_sha256") is True, "Drupal further replacement allocation/current epoch binding")
    require(value.get("execution_must_match_allocated_manifest_sha256") is True, "Drupal further replacement execution/allocation epoch binding")


def validate_drupal_replacement_authorization_state(repo: Path) -> tuple[str | None, set[str]]:
    identities = directory_identities(repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT)
    require(len(identities) <= 1, "more than one Drupal replacement identity")
    if not identities:
        return None, set()
    run_id = next(iter(identities))
    require(REHEARSAL_RUN.fullmatch(run_id) is not None and "-drupal-" in run_id and run_id != FAILED_DRUPAL_RUN_ID, "invalid Drupal replacement identity")
    root = repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT / run_id
    require({path.name for path in root.iterdir()} == {"authorization.json"}, "Drupal replacement authorization inventory")
    path = root / "authorization.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("record_type") == "ONE_RUN_DRUPAL_REPLACEMENT_AUTHORIZATION" and value.get("run_id") == run_id, "Drupal replacement authorization record")
    require(value.get("replacement_admission_anchor_sha256") == DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA, "Drupal replacement authorization anchor")
    require(value.get("repaired_installed_source_manifest_sha256") == DRUPAL_REPLACEMENT_HISTORICAL_SOURCE_MANIFEST_SHA, "Drupal replacement historical authorization source epoch")
    require(value.get("failed_run_id") == FAILED_DRUPAL_RUN_ID and value.get("failed_family_aggregate_sha256") == FAILED_DRUPAL_FAMILY_AGGREGATE_SHA, "Drupal replacement failed-family binding")
    require(value.get("failed_status") == "FAILED_PRESERVED" and value.get("replacement_reason") == "SOURCE_RUNTIME_INSTRUMENTATION_DEFECT", "Drupal replacement classification")
    require(value.get("maximum_new_identities") == 1 and value.get("original_start_authorization_carried_forward") is False, "Drupal replacement one-use policy")
    require(value.get("automatic_retry_authorized") is False and value.get("additional_replacement_identities_authorized") == 0, "Drupal replacement no-retry policy")
    require(value.get("replacement_start_requires_separate_human_authorization") is True and value.get("execution_authorized") is False, "Drupal replacement execution separation")
    return run_id, {path.relative_to(repo).as_posix()}


def validate_drupal_further_replacement_authorization_state(repo: Path) -> tuple[str | None, set[str]]:
    identities = directory_identities(repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT)
    require(len(identities) <= 1, "more than one Drupal further replacement identity")
    if not identities:
        return None, set()
    run_id = next(iter(identities))
    require(run_id == FINAL_FAILED_DRUPAL_RUN_ID and REHEARSAL_RUN.fullmatch(run_id) is not None, "exact final Drupal further replacement identity required")
    root = repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT / run_id
    require({path.name for path in root.iterdir()} == {"authorization.json"}, "Drupal further replacement authorization inventory")
    path = root / "authorization.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("record_type") == "ONE_RUN_DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION" and value.get("run_id") == run_id, "Drupal further replacement authorization record")
    require(value.get("further_replacement_admission_anchor_sha256") == DRUPAL_FURTHER_REPLACEMENT_ADMISSION_SHA, "Drupal further replacement authorization anchor")
    require(value.get("repaired_installed_source_manifest_sha256") == POST_SIGKILL_PREDECESSOR_SOURCE_MANIFEST_SHA, "Drupal further replacement historical authorization source epoch")
    require(value.get("failed_replacement_run_id") == FAILED_DRUPAL_REPLACEMENT_RUN_ID and value.get("failed_replacement_family_aggregate_sha256") == FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA, "Drupal further replacement failed-family binding")
    require(value.get("replacement_reason") == "PROCESS_IDENTITY_VERIFICATION_INSTRUMENTATION_DEFECT", "Drupal further replacement reason")
    require(value.get("maximum_new_identities") == 1 and value.get("automatic_retry_authorized") is False and value.get("additional_replacement_identities_authorized") == 0, "Drupal further replacement one-use policy")
    require(value.get("execution_authorized") is False and value.get("further_replacement_start_requires_separate_human_authorization") is True, "Drupal further replacement execution separation")
    require(value.get("historical_start_authorizations_carried_forward") is False, "Drupal further replacement consumed-token carry-forward")
    return run_id, {path.relative_to(repo).as_posix()}


def expected_non_experimental_cleanup(evidence: Path, failed_path: Path) -> dict[str, Any]:
    """Independently derive cleanup from the process layer that observed it."""
    none = {
        "required": False,
        "signal": None,
        "classification": "NONE",
        "source": "NONE",
        "outer_process_timed_out": False,
        "supervisor_internal_timeout": False,
        "evidence_path": None,
        "evidence_sha256": None,
    }
    if not failed_path.is_file():
        return none
    failed = json.loads(failed_path.read_text(encoding="utf-8"))
    outer = failed.get("diagnostic", {})
    require(isinstance(outer, dict), "failure diagnostic must be an object")
    outer_signal = outer.get("cleanup_signal")
    outer_timeout = outer.get("timed_out") is True
    require(
        outer_signal is None or (
            isinstance(outer_signal, int)
            and outer_signal > 0
            and outer.get("cleanup_is_not_experimental_sigkill") is True
            and outer.get("experimental_sigkill_delivered") is False
        ),
        "outer cleanup classification is contradictory",
    )

    supervisor_path = evidence / "crewai-startup-diagnostic.json"
    require(
        supervisor_path.is_file() == (failed.get("crewai_startup_diagnostic_sha256") is not None),
        "CrewAI supervisor diagnostic/binding presence mismatch",
    )
    if supervisor_path.is_file():
        supervisor_sha = sha(supervisor_path)
        require(
            failed.get("crewai_startup_diagnostic_sha256") == supervisor_sha,
            "CrewAI supervisor diagnostic is not bound by the failure record",
        )
        supervisor = json.loads(supervisor_path.read_text(encoding="utf-8"))
        require(
            supervisor.get("trial_id") == failed.get("run_id")
            and supervisor.get("framework_origin") == "crewai",
            "CrewAI supervisor diagnostic identity",
        )
        supervisor_required = supervisor.get("cleanup_termination_required")
        supervisor_signal = supervisor.get("cleanup_signal_observed")
        require(isinstance(supervisor_required, bool), "CrewAI supervisor cleanup requirement missing")
        require(
            supervisor.get("experimental_sigkill_delivered") is False
            and supervisor.get("cleanup_is_not_experimental_sigkill") is True,
            "CrewAI supervisor cleanup cannot be experimental termination",
        )
        if supervisor_required:
            require(
                isinstance(supervisor_signal, int)
                and supervisor_signal > 0
                and supervisor.get("worker_returncode") == -supervisor_signal,
                "CrewAI supervisor cleanup signal/return-code mismatch",
            )
        else:
            require(supervisor_signal is None, "CrewAI supervisor reported unrequired cleanup signal")
        supervisor_timeout = supervisor.get("failure_reason") == "timeout_waiting_for_seam"
        if supervisor_timeout:
            require(
                supervisor.get("status") == "FAILED_BEFORE_VERIFIED_SEAM"
                and supervisor.get("seam_ready_verified") is False
                and supervisor.get("timeout_seconds") == 30.0
                and supervisor_required,
                "CrewAI supervisor internal-timeout evidence incomplete",
            )
        if supervisor_required:
            require(outer_signal is None, "cleanup reported by both outer process and supervisor")
            return {
                "required": True,
                "signal": supervisor_signal,
                "classification": "NON_EXPERIMENTAL_TIMEOUT_OR_FAILURE_CLEANUP",
                "source": "SUPERVISOR_DIAGNOSTIC",
                "outer_process_timed_out": outer_timeout,
                "supervisor_internal_timeout": supervisor_timeout,
                "evidence_path": supervisor_path.name,
                "evidence_sha256": supervisor_sha,
            }

    if outer_signal is not None:
        return {
            "required": True,
            "signal": outer_signal,
            "classification": "NON_EXPERIMENTAL_TIMEOUT_OR_FAILURE_CLEANUP",
            "source": "OUTER_COMMAND_DIAGNOSTIC",
            "outer_process_timed_out": outer_timeout,
            "supervisor_internal_timeout": False,
            "evidence_path": failed_path.name,
            "evidence_sha256": sha(failed_path),
        }
    require(not outer_timeout, "outer timeout is missing cleanup signal evidence")
    return none


def validate_experimental_termination(evidence: Path, finalization: dict[str, Any]) -> None:
    expected = []
    for path in sorted(evidence.glob("*-termination.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        require(
            value.get("observed_signal") == 9
            and value.get("actual_worker_terminated") is True,
            f"experimental termination record inconsistent: {path.name}",
        )
        expected.append({
            "path": path.name,
            "status": value.get("status"),
            "observed_signal": value.get("observed_signal"),
            "actual_worker_terminated": value.get("actual_worker_terminated"),
        })
    require(finalization.get("experimental_termination") == {"records": expected}, "experimental termination summary")


def validate_cleanup_classification(
    run_id: str,
    evidence: Path,
    failed_path: Path,
    finalization_path: Path,
    finalization: dict[str, Any],
) -> bool:
    """Return true only for the exact immutable v1.0.13 classification anomaly."""
    cleanup = finalization.get("non_experimental_cleanup")
    if run_id == LEGACY_CLASSIFICATION_RUN_ID:
        require(sha(finalization_path) == LEGACY_CLASSIFICATION_FINALIZATION_SHA, "legacy finalization hash")
        require(sha(failed_path) == LEGACY_CLASSIFICATION_FAILURE_SHA, "legacy failure-record hash")
        diagnostic_path = evidence / "crewai-startup-diagnostic.json"
        require(sha(diagnostic_path) == LEGACY_CLASSIFICATION_DIAGNOSTIC_SHA, "legacy supervisor diagnostic hash")
        expected = expected_non_experimental_cleanup(evidence, failed_path)
        require(
            expected["source"] == "SUPERVISOR_DIAGNOSTIC"
            and expected["supervisor_internal_timeout"] is True
            and expected["signal"] == 9,
            "legacy supervisor timeout/cleanup evidence",
        )
        require(
            cleanup == {"required": False, "signal": None, "classification": "NONE"}
            and finalization.get("outcome") == "FAIL",
            "legacy top-level inconsistency must remain exact",
        )
        print(
            "[PASS] KNOWN_HISTORICAL_CLASSIFICATION_INCONSISTENCY: exact immutable v1.0.13 "
            "family retained as FAIL; supervisor signal-9 cleanup is proven but its top-level record remains NONE"
        )
        return True
    require(cleanup == expected_non_experimental_cleanup(evidence, failed_path), "non-experimental cleanup classification")
    return False


def offline_rehearsal_identities(identities: set[str]) -> set[str]:
    """Select only semantic offline rehearsal identities, never Drupal/reset families."""
    return {
        run_id for run_id in identities
        if (match := REHEARSAL_RUN.fullmatch(run_id)) is not None and match.group(1) == "offline"
    }


def select_corrected_environment_identity(
    repo: Path,
    transition_ids: set[str],
    historical: set[str],
) -> str | None:
    """Select one authorized corrected offline family from a mixed lifecycle set."""
    corrected_ids = offline_rehearsal_identities(transition_ids) - historical
    require(len(corrected_ids) <= 1, f"more than one corrected-environment identity: {sorted(corrected_ids)}")
    corrected_id = next(iter(corrected_ids), None)
    if corrected_id is None:
        return None
    authorization_path = repo / AUTHORIZATION_ROOT / corrected_id / "authorization.json"
    require(authorization_path.is_file(), "corrected-environment authorization record required")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    require(
        authorization.get("record_type") == "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION"
        and authorization.get("corrected_environment_admission_anchor_sha256") == CORRECTED_ADMISSION_ANCHOR_SHA,
        "corrected-environment identity must be anchored by its authorization record",
    )
    return corrected_id


def _validate_one_run_transition(repo: Path, ignored_ids: set[str] | None = None) -> tuple[str | None, set[str]]:
    """Validate one admission transition while explicitly excluding another bound transition."""
    ignored = ignored_ids or set()
    authorization_root = repo / AUTHORIZATION_ROOT
    preservation_root = repo / PRESERVATION_ROOT
    authorization_ids = offline_rehearsal_identities(directory_identities(authorization_root)) - ignored
    preservation_ids = offline_rehearsal_identities(directory_identities(preservation_root)) - ignored
    evidence_ids = offline_rehearsal_identities(directory_identities(repo / REHEARSAL_EVIDENCE_ROOT))
    runtime_ids = offline_rehearsal_identities(directory_identities(repo / RUNTIME_ROOT))
    extra_evidence = evidence_ids - BASELINE_RUN_IDS - ignored
    extra_runtime = runtime_ids - BASELINE_RUN_IDS - ignored
    all_new = authorization_ids | preservation_ids | extra_evidence | extra_runtime
    require(len(all_new) <= 1, f"unrelated or second successor identity: {sorted(all_new)}")
    if not all_new:
        require(evidence_ids == BASELINE_RUN_IDS and runtime_ids == BASELINE_RUN_IDS, "historical identity baseline")
        return None, set()
    run_id = next(iter(all_new))
    require(REHEARSAL_RUN.fullmatch(run_id) is not None and "-offline-" in run_id, "successor must be one offline identity")
    require(authorization_ids == {run_id}, "successor authorization record required")
    authorization_dir = authorization_root / run_id
    require({path.name for path in authorization_dir.iterdir()} == {"authorization.json"}, "authorization exact file inventory")
    authorization_path = authorization_dir / "authorization.json"
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if run_id == LEGACY_CLASSIFICATION_RUN_ID:
        require(set(authorization) == {
            "$schema", "schema_version", "record_type", "run_id", "authorized_at",
            "authorization_boundary", "admission_anchor_sha256",
            "predecessor_source_manifest_sha256", "historical_inventory_sha256",
            "maximum_new_identities", "replacement_or_retry_authorized", "scope",
        }, "consumed authorization record fields")
        require(authorization.get("record_type") == "ONE_RUN_AUTHORIZATION" and authorization.get("run_id") == run_id, "consumed authorization identity")
        require(authorization.get("authorization_boundary") == "explicit_human_authorization_before_worker_execution", "consumed authorization boundary")
        require(authorization.get("admission_anchor_sha256") == ADMISSION_ANCHOR_SHA, "consumed authorization anchor")
        require(authorization.get("predecessor_source_manifest_sha256") == PREDECESSOR_SOURCE_MANIFEST_SHA, "consumed authorization source predecessor")
        require(authorization.get("historical_inventory_sha256") == HISTORICAL_INVENTORY_SHA, "consumed authorization historical predecessor")
        require(authorization.get("maximum_new_identities") == 1 and authorization.get("replacement_or_retry_authorized") is False, "consumed authorization single-use policy")
    elif run_id == REPLACEMENT_FAIL_RUN_ID:
        require(set(authorization) == {
            "$schema", "schema_version", "record_type", "run_id", "authorized_at",
            "authorization_boundary", "replacement_admission_anchor_sha256",
            "v1_0_14_source_manifest_sha256", "consumed_run_id",
            "consumed_authorization_sha256", "historical_fail_finalization_sha256",
            "retained_baseline_inventory_sha256", "maximum_new_identities",
            "consumed_admission_reopened", "historical_identity_reuse_authorized",
            "automatic_replacement_or_retry_authorized",
            "additional_replacement_identities_authorized", "scope",
        }, "replacement authorization record fields")
        require(authorization.get("record_type") == "ONE_RUN_REPLACEMENT_AUTHORIZATION" and authorization.get("run_id") == run_id, "replacement authorization identity")
        require(authorization.get("authorization_boundary") == "separate_explicit_human_replacement_authorization_before_identity_creation", "replacement authorization boundary")
        require(authorization.get("replacement_admission_anchor_sha256") == REPLACEMENT_ADMISSION_ANCHOR_SHA, "replacement authorization anchor")
        require(authorization.get("v1_0_14_source_manifest_sha256") == V1_0_14_SOURCE_MANIFEST_SHA, "replacement source predecessor")
        require(authorization.get("consumed_run_id") == LEGACY_CLASSIFICATION_RUN_ID, "replacement consumed identity binding")
        require(authorization.get("consumed_authorization_sha256") == "c5827b91aae862dca52ecfc7b6618e0ef1e007404cc68c029da5929a7a8ecfb3", "replacement consumed authorization binding")
        require(authorization.get("historical_fail_finalization_sha256") == LEGACY_CLASSIFICATION_FINALIZATION_SHA, "replacement finalized FAIL binding")
        require(authorization.get("retained_baseline_inventory_sha256") == RETAINED_BASELINE_INVENTORY_SHA, "replacement retained baseline binding")
        require(authorization.get("maximum_new_identities") == 1, "replacement maximum identities")
        require(authorization.get("consumed_admission_reopened") is False and authorization.get("historical_identity_reuse_authorized") is False, "replacement historical closure")
        require(authorization.get("automatic_replacement_or_retry_authorized") is False and authorization.get("additional_replacement_identities_authorized") == 0, "replacement no-retry policy")
        require(sha(authorization_path) == REPLACEMENT_FAIL_AUTHORIZATION_SHA, "replacement authorization hash")
    else:
        require(set(authorization) == {
            "$schema", "schema_version", "record_type", "run_id", "authorized_at",
            "authorization_boundary", "corrected_environment_admission_anchor_sha256",
            "installed_source_manifest_sha256", "historical_run_ids",
            "historical_finalization_sha256", "representative_startup_preservation_manifest_sha256",
            "identity_allocation_preflight_sha256", "identity_allocation_preflight",
            "maximum_new_identities", "historical_identity_reuse_authorized",
            "automatic_replacement_or_retry_authorized", "additional_identities_authorized", "scope",
        }, "corrected-environment authorization record fields")
        require(authorization.get("record_type") == "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION" and authorization.get("run_id") == run_id, "corrected-environment authorization identity")
        require(authorization.get("authorization_boundary") == "fresh_corrected_environment_preflight_before_identity_allocation", "corrected-environment authorization boundary")
        require(authorization.get("corrected_environment_admission_anchor_sha256") == CORRECTED_ADMISSION_ANCHOR_SHA, "corrected-environment authorization anchor")
        require(
            authorization.get("installed_source_manifest_sha256") == CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA,
            "corrected-environment historical installed source binding",
        )
        require(authorization.get("historical_run_ids") == [LEGACY_CLASSIFICATION_RUN_ID, REPLACEMENT_FAIL_RUN_ID], "corrected-environment historical identities")
        require(authorization.get("historical_finalization_sha256") == [LEGACY_CLASSIFICATION_FINALIZATION_SHA, REPLACEMENT_FAIL_FINALIZATION_SHA], "corrected-environment historical finalizations")
        require(authorization.get("representative_startup_preservation_manifest_sha256") == CORRECTED_STARTUP_PRESERVATION_SHA, "corrected-environment representative PASS binding")
        validate_corrected_environment_preflight(authorization.get("identity_allocation_preflight", {}))
        require(authorization.get("identity_allocation_preflight_sha256") == canonical_sha(authorization["identity_allocation_preflight"]), "corrected-environment preflight hash")
        require(authorization.get("maximum_new_identities") == 1 and authorization.get("historical_identity_reuse_authorized") is False, "corrected-environment one-run policy")
        require(authorization.get("automatic_replacement_or_retry_authorized") is False and authorization.get("additional_identities_authorized") == 0, "corrected-environment no retry policy")
    authorized_at = datetime.fromisoformat(authorization["authorized_at"].replace("Z", "+00:00"))
    authorization_sha = sha(authorization_path)
    transition_paths = {authorization_path.relative_to(repo).as_posix()}
    if not extra_evidence and not extra_runtime and not preservation_ids:
        return run_id, transition_paths
    require(extra_evidence == {run_id} and extra_runtime == {run_id}, "authorized successor requires matching evidence and runtime roots")
    require(preservation_ids == {run_id}, "started successor requires finalization; interrupted finalization fails closed")
    evidence = repo / REHEARSAL_EVIDENCE_ROOT / run_id
    runtime = repo / RUNTIME_ROOT / run_id
    preservation = preservation_root / run_id
    preservation_names = {path.name for path in preservation.iterdir()}
    require(preservation_names in ({"finalization.json"}, {"finalization.json", "post-inspection.json"}), "preservation exact file inventory")
    transition_paths |= {path.relative_to(repo).as_posix() for path in preservation.iterdir() if path.is_file()}
    finalization_path = preservation / "finalization.json"
    finalization = json.loads(finalization_path.read_text(encoding="utf-8"))
    require(finalization.get("record_type") == "ONE_RUN_FINALIZATION" and finalization.get("run_id") == run_id, "finalization identity")
    require(finalization.get("authorization_sha256") == authorization_sha, "finalization authorization binding")
    require(finalization.get("workers_stopped") is True and finalization.get("open_writer_count") == 0, "finalization writer status")
    require(finalization.get("integrity_status") == "FINALIZED_AND_HASH_BOUND", "finalization integrity status")
    require(finalization.get("certification_status") == "NOT_HUMAN_CERTIFIED", "finalization certification separation")
    finalized_at = datetime.fromisoformat(finalization["finalized_at"].replace("Z", "+00:00"))
    require(authorized_at < finalized_at, "authorization must precede finalization")
    evidence_expected = validate_inventory_entries(evidence, finalization.get("evidence_inventory"), "successor evidence")
    runtime_expected = validate_inventory_entries(runtime, finalization.get("runtime_inventory"), "successor runtime")
    require(canonical_sha(finalization["evidence_inventory"]) == finalization.get("evidence_inventory_sha256"), "evidence inventory digest")
    require(canonical_sha(finalization["runtime_inventory"]) == finalization.get("runtime_inventory_sha256"), "runtime inventory digest")
    binding = json.loads((runtime / "authorization-binding.json").read_text(encoding="utf-8"))
    require(binding.get("run_id") == run_id and binding.get("authorization_sha256") == authorization_sha, "pre-worker runtime authorization binding")
    require(binding.get("bound_before_worker_execution") is True and binding.get("authorized_at") == authorization["authorized_at"], "authorization chronology binding")
    evidence_actual = actual_inventory(evidence)
    runtime_actual = actual_inventory(runtime)
    addendum_path = preservation / "post-inspection.json"
    additions = {"evidence": {}, "runtime": {}}
    if addendum_path.is_file():
        addendum = json.loads(addendum_path.read_text(encoding="utf-8"))
        require(addendum.get("record_type") == "POST_INSPECTION_ADDENDUM" and addendum.get("run_id") == run_id, "post-inspection identity")
        require(addendum.get("finalization_sha256") == sha(finalization_path), "post-inspection finalization binding")
        require(addendum.get("classification") == "POST_INSPECTION_NOT_EXPERIMENTAL_STATE", "post-inspection provenance")
        for entry in addendum.get("artifacts", []):
            require(isinstance(entry, dict) and set(entry) == {"path", "size", "sha256"}, "post-inspection entry")
            prefix, relative = entry["path"].split("/", 1)
            require(prefix in additions and relative not in additions[prefix], "post-inspection path")
            additions[prefix][relative] = {**entry, "path": relative}
    require(evidence_actual == evidence_expected | additions["evidence"], "successor evidence inventory drift or unclassified post-inspection artifact")
    require(runtime_actual == runtime_expected | additions["runtime"], "successor runtime inventory drift or unclassified post-inspection artifact")
    outcome = finalization.get("outcome")
    require(outcome in {"PASS", "FAIL", "TIMEOUT"}, "finalization outcome")
    failed_path = evidence / "FAILED-ATTEMPT.json"
    manifest_path = evidence / "evidence-manifest.json"
    validate_experimental_termination(evidence, finalization)
    if outcome == "PASS":
        require(manifest_path.is_file() and not failed_path.exists(), "PASS family evidence state")
        require(finalization.get("canonical_success_manifest") == "VERIFIED", "PASS manifest classification")
        validate_cleanup_classification(run_id, evidence, failed_path, finalization_path, finalization)
        from gate2c_step02_certify import validate_offline
        validate_offline(evidence)
    else:
        require(failed_path.is_file() and not manifest_path.exists(), "failed family cannot carry success manifest")
        require(finalization.get("canonical_success_manifest") == "PROHIBITED_FOR_NON_PASS", "failed manifest classification")
        failed = json.loads(failed_path.read_text(encoding="utf-8"))
        require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id and failed.get("outcome") == outcome, "failed family outcome binding")
        validate_cleanup_classification(run_id, evidence, failed_path, finalization_path, finalization)
    for path in sorted(evidence.rglob("*.json")):
        assert_zero_external_activity(json.loads(path.read_text(encoding="utf-8")))
    scan_evidence(evidence)
    scan_evidence(runtime)
    return run_id, transition_paths


def validate_one_run_transition(repo: Path) -> tuple[str | None, set[str], set[str]]:
    """Validate two immutable FAIL transitions and at most one corrected transition."""
    authorization_ids = offline_rehearsal_identities(directory_identities(repo / AUTHORIZATION_ROOT))
    preservation_ids = offline_rehearsal_identities(directory_identities(repo / PRESERVATION_ROOT))
    evidence_ids = offline_rehearsal_identities(directory_identities(repo / REHEARSAL_EVIDENCE_ROOT)) - BASELINE_RUN_IDS
    runtime_ids = offline_rehearsal_identities(directory_identities(repo / RUNTIME_ROOT)) - BASELINE_RUN_IDS
    all_transition_ids = authorization_ids | preservation_ids | evidence_ids | runtime_ids
    historical = {LEGACY_CLASSIFICATION_RUN_ID, REPLACEMENT_FAIL_RUN_ID}
    require(historical <= all_transition_ids, "historical governed transitions missing")
    corrected_id = select_corrected_environment_identity(repo, all_transition_ids, historical)
    consumed_id, consumed_paths = _validate_one_run_transition(
        repo,
        ignored_ids={REPLACEMENT_FAIL_RUN_ID} | ({corrected_id} if corrected_id else set()),
    )
    require(consumed_id == LEGACY_CLASSIFICATION_RUN_ID, "consumed transition identity")
    transition_paths = set(consumed_paths)
    observed_replacement, replacement_paths = _validate_one_run_transition(
        repo,
        ignored_ids={LEGACY_CLASSIFICATION_RUN_ID} | ({corrected_id} if corrected_id else set()),
    )
    require(observed_replacement == REPLACEMENT_FAIL_RUN_ID, "replacement transition identity")
    transition_paths |= replacement_paths
    if corrected_id is not None:
        observed_corrected, corrected_paths = _validate_one_run_transition(repo, ignored_ids=historical)
        require(observed_corrected == corrected_id, "corrected-environment transition identity")
        transition_paths |= corrected_paths
    runtime_transition_ids = {
        run_id for run_id in historical | ({corrected_id} if corrected_id else set())
        if run_id is not None and (repo / RUNTIME_ROOT / run_id).is_dir()
    }
    return corrected_id, transition_paths, runtime_transition_ids


def validate_untracked_inventory(untracked: set[str], evidence_untracked: set[str], transition_untracked: set[str]) -> None:
    allowed = PROTECTED | INSTALLED_SOURCES | {SOURCE_MANIFEST} | evidence_untracked | transition_untracked
    require(not (untracked - allowed), f"unexpected untracked paths: {sorted(untracked - allowed)}")
    require(not (PROTECTED - untracked), f"protected local-only path missing or no longer untracked: {sorted(PROTECTED - untracked)}")


def validate_support_installation_boundary(untracked: set[str]) -> None:
    """Reject lifecycle evidence at the support-only installation boundary."""
    rehearsal_prefix = f"{REHEARSAL_EVIDENCE_ROOT}/"
    prohibited = {
        relative for relative in untracked
        if (
            relative.startswith(f"{rehearsal_prefix}gate2c-step02-drupal-")
            and not relative.startswith(f"{rehearsal_prefix}{FAILED_DRUPAL_RUN_ID}/")
        )
        or relative.startswith(f"{rehearsal_prefix}gate2c-step02-reset-")
        or relative.startswith("evidence/gates/gate-2c/step02-certification/")
    }
    require(not prohibited, f"premature Drupal/reset/certification evidence: {sorted(prohibited)}")


def validate_crewai_decision_value(value: dict[str, Any]) -> None:
    """Validate the immutable human decision independently of filesystem bindings."""
    require(value.get("schema_version") == 2, "CrewAI decision schema version")
    require(value.get("decision_id") == DECISION_ID, "CrewAI decision identity")
    require(value.get("rehearsal_run_id") == CORRECTED_PASS_RUN_ID, "CrewAI decision rehearsal identity")
    require(value.get("contract_sha256") == CONTRACT_SHA, "CrewAI decision contract")
    require(value.get("candidate") == "public SQLiteFlowPersistence.load_state plus public Flow.kickoff inputs id hydration of the same Flow identity", "CrewAI decision candidate")
    require(value.get("machine_recommendation") == "APPROVAL_READY", "CrewAI machine recommendation")
    require(value.get("human_decision") == "APPROVED" and value.get("decided_by") == "human_operator", "CrewAI human decision")
    require(value.get("scope") == "Gate_2C_CrewAI_process_recovery_architecture_only_no_live_execution_authorization", "CrewAI decision scope")

    authorization = value.get("authorization_binding", {})
    require(authorization == {
        "authorization_path": f"{AUTHORIZATION_ROOT}/{CORRECTED_PASS_RUN_ID}/authorization.json",
        "authorization_sha256": CORRECTED_PASS_AUTHORIZATION_SHA,
        "authorization_record_type": "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION",
        "identity_allocation_preflight_sha256": CORRECTED_PASS_ALLOCATION_PREFLIGHT_SHA,
        "runtime_authorization_binding_path": f"{RUNTIME_ROOT}/{CORRECTED_PASS_RUN_ID}/authorization-binding.json",
        "runtime_authorization_binding_sha256": CORRECTED_PASS_RUNTIME_BINDING_SHA,
        "execution_preflight_sha256": CORRECTED_PASS_EXECUTION_PREFLIGHT_SHA,
        "rehearsal_installed_source_manifest_path": SOURCE_MANIFEST,
        "rehearsal_installed_source_manifest_sha256": CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA,
    }, "CrewAI decision authorization/preflight/source binding")

    evidence_root = f"{REHEARSAL_EVIDENCE_ROOT}/{CORRECTED_PASS_RUN_ID}"
    preservation_root = f"{PRESERVATION_ROOT}/{CORRECTED_PASS_RUN_ID}"
    require(value.get("pass_family_binding") == {
        "evidence_root": evidence_root,
        "evidence_manifest_path": f"{evidence_root}/evidence-manifest.json",
        "evidence_manifest_sha256": CORRECTED_PASS_EVIDENCE_MANIFEST_SHA,
        "finalization_path": f"{preservation_root}/finalization.json",
        "finalization_sha256": CORRECTED_PASS_FINALIZATION_SHA,
        "outcome": "PASS",
        "integrity_status": "FINALIZED_AND_HASH_BOUND",
        "certification_status": "NOT_HUMAN_CERTIFIED",
    }, "CrewAI decision PASS family binding")

    history = value.get("diagnostic_environment_history", {})
    require(history.get("corrected_environment_admission_path") == CORRECTED_ADMISSION_ANCHOR, "CrewAI decision corrected admission path")
    require(history.get("corrected_environment_admission_sha256") == CORRECTED_ADMISSION_ANCHOR_SHA, "CrewAI decision corrected admission hash")
    require(history.get("execution_environment_finding_path") == ENVIRONMENT_FINDING, "CrewAI decision environment finding path")
    require(history.get("execution_environment_finding_sha256") == ENVIRONMENT_FINDING_SHA, "CrewAI decision environment finding hash")
    require(history.get("historical_inventory_sha256") == HISTORICAL_INVENTORY_SHA, "CrewAI decision historical inventory")
    require(history.get("retained_baseline_inventory_sha256") == RETAINED_BASELINE_INVENTORY_SHA, "CrewAI decision retained baseline")
    require(history.get("historical_finalizations") == [
        {
            "run_id": LEGACY_CLASSIFICATION_RUN_ID,
            "path": f"{PRESERVATION_ROOT}/{LEGACY_CLASSIFICATION_RUN_ID}/finalization.json",
            "sha256": LEGACY_CLASSIFICATION_FINALIZATION_SHA,
            "outcome": "FAIL",
        },
        {
            "run_id": REPLACEMENT_FAIL_RUN_ID,
            "path": f"{PRESERVATION_ROOT}/{REPLACEMENT_FAIL_RUN_ID}/finalization.json",
            "sha256": REPLACEMENT_FAIL_FINALIZATION_SHA,
            "outcome": "FAIL",
        },
    ], "CrewAI decision historical finalizations")
    require(history.get("preservation_manifests") == [
        {"package": package, "sha256": digest}
        for package, digest in DIAGNOSTIC_PRESERVATIONS.items()
    ], "CrewAI decision diagnostic/environment history")

    require(value.get("lifecycle_boundary") == {
        "step_2c02_certification": "NOT_PERFORMED",
        "gate_2c": "DEFERRED_UNCLAIMED",
        "gate_2": "NOT_COMPLETE",
        "additional_rehearsal_authorized": False,
        "step_2c03_authorized": False,
        "latest_pointer_update_authorized": False,
    }, "CrewAI decision lifecycle separation")


def validate_crewai_decision_inventory(paths: set[str], installed: bool) -> None:
    """Enforce the already-installed singular decision in both repair modes."""
    del installed
    require(paths == {DECISION_PATH}, "exactly one installed CrewAI architecture decision")


def validate_crewai_decision(repo: Path, content: Path, decision_root: Path) -> None:
    """Validate schema, uniqueness, exact PASS bindings, and unchanged history."""
    schema = json.loads((content / DECISION_SCHEMA).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    decision = decision_root / DECISION_PATH
    require(decision.is_file() and not decision.is_symlink(), "CrewAI decision record missing")
    value = json.loads(decision.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(value)
    validate_crewai_decision_value(value)
    scan_evidence(decision.parent)

    authorization = repo / value["authorization_binding"]["authorization_path"]
    runtime_binding = repo / value["authorization_binding"]["runtime_authorization_binding_path"]
    evidence_manifest = repo / value["pass_family_binding"]["evidence_manifest_path"]
    finalization_path = repo / value["pass_family_binding"]["finalization_path"]
    require(sha(authorization) == CORRECTED_PASS_AUTHORIZATION_SHA, "CrewAI decision authorization drift")
    require(sha(runtime_binding) == CORRECTED_PASS_RUNTIME_BINDING_SHA, "CrewAI decision runtime authorization binding drift")
    require(sha(evidence_manifest) == CORRECTED_PASS_EVIDENCE_MANIFEST_SHA, "CrewAI decision evidence manifest drift")
    require(sha(finalization_path) == CORRECTED_PASS_FINALIZATION_SHA, "CrewAI decision finalization drift")

    authorization_value = json.loads(authorization.read_text(encoding="utf-8"))
    runtime_value = json.loads(runtime_binding.read_text(encoding="utf-8"))
    finalization = json.loads(finalization_path.read_text(encoding="utf-8"))
    require(authorization_value.get("record_type") == "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION", "CrewAI decision authorization type")
    require(authorization_value.get("identity_allocation_preflight_sha256") == CORRECTED_PASS_ALLOCATION_PREFLIGHT_SHA, "CrewAI decision allocation preflight")
    require(authorization_value.get("installed_source_manifest_sha256") == CORRECTED_PASS_INSTALLED_SOURCE_MANIFEST_SHA, "CrewAI decision rehearsal source manifest")
    require(runtime_value.get("execution_preflight_sha256") == CORRECTED_PASS_EXECUTION_PREFLIGHT_SHA and runtime_value.get("execution_preflight_passed_before_family_creation") is True, "CrewAI decision execution preflight")
    require(finalization.get("outcome") == "PASS" and finalization.get("integrity_status") == "FINALIZED_AND_HASH_BOUND", "CrewAI decision finalized PASS")
    require(finalization.get("certification_status") == "NOT_HUMAN_CERTIFIED", "CrewAI decision certification separation")
    from gate2c_step02_certify import validate_offline
    validate_offline(repo / value["pass_family_binding"]["evidence_root"])

    for item in value["diagnostic_environment_history"]["historical_finalizations"]:
        require(sha(repo / item["path"]) == item["sha256"], "CrewAI decision historical finalization drift")
    require(sha(repo / CORRECTED_ADMISSION_ANCHOR) == CORRECTED_ADMISSION_ANCHOR_SHA, "CrewAI decision corrected admission drift")
    require(sha(repo / ENVIRONMENT_FINDING) == ENVIRONMENT_FINDING_SHA, "CrewAI decision environment finding drift")
    for item in value["diagnostic_environment_history"]["preservation_manifests"]:
        require(sha(EXTERNAL_PACKAGE_ROOT / item["package"] / "preservation-manifest.json") == item["sha256"], "CrewAI decision diagnostic preservation drift")


def validate_architecture_decision_lifecycle_docs(content: Path) -> None:
    """Keep architecture approval separate from certification and later lifecycle work."""
    documents = {
        "AGENTS.md": ("human-approved", "Step 2C.02 remains incomplete and uncertified", "Gate 2C remains `DEFERRED_UNCLAIMED`"),
        "PLAN.md": ("human-approved", "Step 2C.02 remains incomplete and uncertified", "Gate 2 remains `NOT_COMPLETE`"),
        "README.md": ("human-approved", "Step 2C.02 remains incomplete and uncertified", "Gate 2C remains `DEFERRED_UNCLAIMED`"),
        "docs/CURRENT-STATUS.md": ("human-approved", "Step 2C.02 remains incomplete and uncertified", "Gate 2 overall remains `NOT_COMPLETE`"),
        "docs/gates/GATE-2C-STEP02-SHARED-FAILURE-INJECTOR-AND-MODEL-FREE-REHEARSALS.md": ("human operator separately", "does not certify Step 2C.02", "or authorize Step 2C.03"),
    }
    for relative, phrases in documents.items():
        value = (content / relative).read_text(encoding="utf-8")
        require(all(phrase in value for phrase in phrases), f"architecture-decision lifecycle wording: {relative}")


def validate_rehearsal_evidence(repo: Path, untracked: set[str]) -> set[str]:
    prefix = f"{REHEARSAL_EVIDENCE_ROOT}/"
    evidence_paths = {path for path in untracked if path.startswith(prefix)}
    grouped: dict[str, set[str]] = {}
    for relative in evidence_paths:
        remainder = relative.removeprefix(prefix)
        parts = remainder.split("/")
        require(len(parts) == 2 and all(parts), f"unexpected rehearsal evidence path: {relative}")
        grouped.setdefault(parts[0], set()).add(parts[1])
    for run_id, names in sorted(grouped.items()):
        match = REHEARSAL_RUN.fullmatch(run_id)
        require(match is not None, f"unexpected rehearsal evidence identity: {run_id}")
        root = repo / REHEARSAL_EVIDENCE_ROOT / run_id
        require(root.is_dir() and not root.is_symlink(), f"rehearsal evidence root: {run_id}")
        require({path.name for path in root.iterdir() if path.is_file()} == names, f"rehearsal evidence file inventory: {run_id}")
        if run_id == FAILED_DRUPAL_RUN_ID:
            require(names == set(FAILED_DRUPAL_EVIDENCE), "failed Drupal evidence exact file set")
            verify_path_hashes(root, FAILED_DRUPAL_EVIDENCE, "failed Drupal evidence")
            failed = json.loads((root / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
            require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id, "failed Drupal evidence classification")
            require("evidence-manifest.json" not in names, "failed Drupal family cannot be accepted")
            scan_evidence(root)
            continue
        if run_id == FAILED_DRUPAL_REPLACEMENT_RUN_ID:
            require(names == set(FAILED_DRUPAL_REPLACEMENT_EVIDENCE), "failed Drupal replacement evidence exact file set")
            verify_path_hashes(root, FAILED_DRUPAL_REPLACEMENT_EVIDENCE, "failed Drupal replacement evidence")
            failed = json.loads((root / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
            require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id, "failed Drupal replacement evidence classification")
            require("evidence-manifest.json" not in names and "drupal-termination.json" not in names, "failed Drupal replacement cannot be accepted")
            scan_evidence(root)
            continue
        if run_id == FINAL_FAILED_DRUPAL_RUN_ID:
            require(names == set(FINAL_FAILED_DRUPAL_EVIDENCE), "final failed Drupal evidence exact file set")
            verify_path_hashes(root, FINAL_FAILED_DRUPAL_EVIDENCE, "final failed Drupal evidence")
            failed = json.loads((root / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
            require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id, "final failed Drupal evidence classification")
            require("drupal-termination.json" not in names and "drupal-immediate.json" not in names and "evidence-manifest.json" not in names, "final failed Drupal cannot satisfy passing proof")
            scan_evidence(root)
            continue
        if run_id in QUARANTINED_FAILED_ATTEMPTS:
            expected = QUARANTINED_FAILED_ATTEMPTS[run_id]
            require(names == set(expected), f"quarantined failed-attempt file set: {run_id}")
            verify_path_hashes(root, expected, "quarantined failed-attempt evidence")
            failed = json.loads((root / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
            require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id, "quarantined failed-attempt classification")
            scan_evidence(root)
            continue
        kind = match.group(1)
        expected = REHEARSAL_FILES[kind]
        stack_summary_sha = validate_startup_stack_runtime(repo, run_id) if kind == "startup" else None
        if kind == "async":
            validate_async_runtime(repo, root, run_id)
        if kind == "memory":
            validate_memory_async_runtime(repo, root, run_id)
        if "FAILED-ATTEMPT.json" in names:
            require("evidence-manifest.json" not in names, f"failed rehearsal cannot be accepted: {run_id}")
            optional_failure_diagnostic = {"crewai-startup-diagnostic.json"} if kind == "offline" else set()
            require(names <= (expected - {"evidence-manifest.json"}) | {"FAILED-ATTEMPT.json"} | optional_failure_diagnostic, f"unexpected failed-rehearsal file: {run_id}")
            failed = json.loads((root / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
            require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == run_id, "failed rehearsal classification")
            if kind == "startup":
                require(failed.get("stack_location_summary_sha256") == stack_summary_sha, "failed startup stack summary binding")
            scan_evidence(root)
            continue
        require(names == expected, f"accepted rehearsal exact file set: {run_id}")
        if kind == "startup":
            verify_manifest(root)
            value = json.loads((root / "crewai-startup.json").read_text(encoding="utf-8"))
            require(value.get("status") == "PASS" and value.get("model_free") is True, "CrewAI startup diagnostic status")
            require(value.get("flow_invoked") is False and value.get("sigkill_delivered") is False, "CrewAI startup diagnostic boundary")
            require(value.get("stack_location_summary_sha256") == stack_summary_sha, "startup stack summary binding")
            scan_evidence(root)
        elif kind in {"async", "memory"}:
            verify_manifest(root)
            scan_evidence(root)
        else:
            from gate2c_step02_certify import validate_drupal, validate_offline, validate_reset
            {"offline": validate_offline, "drupal": validate_drupal, "reset": validate_reset}[kind](root)
    return evidence_paths


def validate_step01_certification_root(root: Path, *, expected_manifest_sha: str) -> None:
    expected_files = {
        "authorization-ledger.json", "contract-certification.json", "evidence-manifest.json",
        "predecessor-bindings.json", "privacy-scan.json", "summary.md",
    }
    require(root.is_dir(), "retained Step 2C.01 certification evidence missing")
    require({path.name for path in root.iterdir() if path.is_file()} == expected_files, "Step 2C.01 evidence file set")
    require(sha(root / "evidence-manifest.json") == expected_manifest_sha, "Step 2C.01 evidence manifest drift")
    verify_manifest(root)
    scan_evidence(root)
    certification = json.loads((root / "contract-certification.json").read_text(encoding="utf-8"))
    require(certification.get("status") == "PASS", "Step 2C.01 certification status")
    require(certification.get("contract_sha256") == CONTRACT_SHA, "Step 2C.01 contract binding")
    require(certification.get("model_free") is True and certification.get("drupal_read_only") is True, "Step 2C.01 operation boundary")
    require(all(certification.get(key) == 0 for key in ("model_generations", "provider_requests", "provider_responses", "runtime_mutations", "failure_injections", "framework_workers_started", "snapshot_operations")), "Step 2C.01 zero-operation accounting")
    require(certification.get("gate_2c") == "DEFERRED_UNCLAIMED" and certification.get("gate_2") == "NOT_COMPLETE", "Step 2C.01 lifecycle")
    bindings = json.loads((root / "predecessor-bindings.json").read_text(encoding="utf-8"))
    require(bindings.get("repository_predecessor") == "c022619e220715be17e541650c261ea0b568704b", "Step 2C.01 repository predecessor binding")
    require(bindings.get("freezes") == {
        "drupal_ai": FREEZES["shared/contracts/GATE1-DRUPAL-AI-FREEZE.json"],
        "langgraph": FREEZES["shared/contracts/GATE2A-LANGGRAPH-FREEZE.json"],
        "crewai": FREEZES["shared/contracts/GATE2B-CREWAI-FREEZE.json"],
    }, "Step 2C.01 predecessor freeze bindings")
    privacy = json.loads((root / "privacy-scan.json").read_text(encoding="utf-8"))
    require(privacy.get("status") == "PASS" and not any(privacy.get(key) for key in ("credentials_retained", "hidden_reasoning_retained", "private_database_content_retained", "raw_image_or_data_url_retained")), "Step 2C.01 privacy evidence")
    authorization = json.loads((root / "authorization-ledger.json").read_text(encoding="utf-8"))
    require(authorization.get("live_gate2c_authorizations_granted") == 0, "Step 2C.01 authorization boundary")
    require(authorization.get("crewai_recovery_architecture_decision") == "PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION", "Step 2C.01 CrewAI decision boundary")


def verify_step01_certification(repo: Path) -> None:
    require((repo / STEP01_POINTER).read_text(encoding="utf-8").strip() == STEP01_EVIDENCE, "Step 2C.01 pointer drift")
    validate_step01_certification_root(repo / STEP01_EVIDENCE, expected_manifest_sha=STEP01_MANIFEST_SHA)


def scan_source(root: Path) -> None:
    for relative in sorted(INSTALL_UPDATE | INSTALL_CREATE):
        path = root / relative
        require(path.is_file(), f"managed source missing: {relative}")
        text = path.read_text(encoding="utf-8", errors="replace")
        labels = sorted(label for label, pattern in PAYLOAD_PATTERNS.items() if pattern.search(text))
        require(not labels, f"managed-source credential payload labels {labels}: {relative}")


def scan_evidence(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            content = path.read_bytes()
            require(not any(token in content for token in STRICT), f"strict retained-evidence privacy failure: {path.name}")


def validate_plan(root: Path) -> None:
    plan_path = root / "shared/contracts/GATE2C-STEP02-MODEL-FREE-REHEARSAL-PLAN.json"
    sidecar = root / "shared/contracts/GATE2C-STEP02-MODEL-FREE-REHEARSAL-PLAN.sha256"
    plan_sha = sha(plan_path)
    require(sidecar.read_text(encoding="utf-8").strip() == f"{plan_sha}  GATE2C-STEP02-MODEL-FREE-REHEARSAL-PLAN.json", "plan sidecar")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    require(plan["gate2c_contract"]["sha256"] == CONTRACT_SHA, "contract binding")
    require(plan["semantic_boundary"] == "after target 6 is fully persisted and before target 7 begins", "seam drift")
    require(plan["failure_class"] == "SIGKILL_ACTUAL_FRAMEWORK_WORKER_AFTER_INDEPENDENT_SEAM_VERIFICATION", "failure mechanism")
    require(plan["crewai_recovery_architecture"]["decision_status"] == "PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION", "CrewAI decision closed early")
    require(plan["drupal_lock_policy"]["lease_seconds"] == 1800 and plan["drupal_lock_policy"]["mutation"] == "PROHIBITED", "lock policy")
    require(plan["lifecycle"]["gate_2c"] == "DEFERRED_UNCLAIMED" and plan["lifecycle"]["gate_2"] == "NOT_COMPLETE", "lifecycle")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--content-root", type=Path)
    parser.add_argument("--mode", choices=["installed", "candidate"], default="installed")
    parser.add_argument("--synthetic-installed-transition", action="store_true")
    parser.add_argument("--support-installation-boundary", action="store_true")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    content = (args.content_root or repo).resolve()
    require(not args.synthetic_installed_transition or args.content_root is not None, "synthetic installed transition requires content root")
    require((repo / ".git").is_dir(), "repository required")
    require(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR, "HEAD"], check=False).returncode == 0, "predecessor is not an ancestor")
    require(sha(repo / "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json") == CONTRACT_SHA, "Gate 2C contract drift")
    for relative, expected in FREEZES.items():
        require(sha(repo / relative) == expected, f"freeze drift: {relative}")
    verify_path_hashes(repo, ACCEPTED_CREWAI_MEMORY_SOURCES, "accepted CrewAI memory source")
    verify_path_hashes(repo, PINNED_CREWAI_TELEMETRY_SOURCES, "pinned CrewAI telemetry source")
    snapshot = repo / SNAPSHOT
    require(snapshot.is_file() and snapshot.stat().st_size == 4112532 and sha(snapshot) == SNAPSHOT_SHA, "retained snapshot drift")
    untracked = set(filter(None, git(repo, "ls-files", "--others", "--exclude-standard").splitlines()))
    if args.support_installation_boundary:
        validate_support_installation_boundary(untracked)
    failed_drupal_paths = validate_failed_drupal_family(repo)
    failed_drupal_replacement_paths = validate_failed_drupal_replacement_family(repo)
    final_failed_drupal_paths = validate_final_failed_drupal_family(repo)
    drupal_replacement_id, drupal_replacement_paths = validate_drupal_replacement_authorization_state(repo)
    drupal_further_replacement_id, drupal_further_replacement_paths = validate_drupal_further_replacement_authorization_state(repo)
    require(drupal_replacement_id == FAILED_DRUPAL_REPLACEMENT_RUN_ID, "exact consumed Drupal replacement authorization required")
    require(drupal_further_replacement_id == FINAL_FAILED_DRUPAL_RUN_ID, "exact consumed final Drupal further replacement authorization required")
    corrected_id, transition_untracked, runtime_transition_ids = validate_one_run_transition(repo)
    rehearsal_untracked = validate_rehearsal_evidence(repo, untracked)
    baseline_rehearsal_untracked = {
        path for path in rehearsal_untracked
        if path.removeprefix(f"{REHEARSAL_EVIDENCE_ROOT}/").split("/", 1)[0] in BASELINE_RUN_IDS
    }
    require(len(baseline_rehearsal_untracked) == 39, "exact fixed twelve-family evidence inventory")
    certification_untracked = {path for path in untracked if path.startswith("evidence/gates/gate-2c/step02-certification/")}
    require(not certification_untracked, "Step 2C.02 certification evidence exists before separate authorization")
    require(not (repo / "evidence/gates/gate-2c/step02-certification/GATE2C-STEP02-LATEST.txt").exists(), "Step 2C.02 certification pointer exists before separate authorization")
    decision_untracked = {path for path in untracked if path.startswith(f"{DECISION_ROOT}/")}
    validate_crewai_decision_inventory(decision_untracked, args.mode == "installed")
    decision_content = content
    validate_crewai_decision(repo, content, decision_content)
    authorization_value = json.loads((repo / AUTHORIZATION_ROOT / CORRECTED_PASS_RUN_ID / "authorization.json").read_text(encoding="utf-8"))
    decision_value = json.loads((decision_content / DECISION_PATH).read_text(encoding="utf-8"))
    validate_source_epoch_values(
        authorization_value.get("installed_source_manifest_sha256", ""),
        decision_value.get("authorization_binding", {}).get("rehearsal_installed_source_manifest_sha256", ""),
        sha(EXTERNAL_PACKAGE_ROOT / HUMAN_DECISION_PACKAGE / "payload" / SOURCE_MANIFEST),
    )
    validate_human_decision_governance_transition(content)
    validate_drupal_reset_support_transition(
        repo,
        content,
        args.mode,
        synthetic_installed=args.synthetic_installed_transition,
    )
    validate_failed_start_repair_transition(
        repo,
        content,
        args.mode,
        synthetic_installed=args.synthetic_installed_transition,
    )
    validate_process_identity_repair_transition(
        repo,
        content,
        args.mode,
        synthetic_installed=args.synthetic_installed_transition,
    )
    validate_post_sigkill_repair_transition(
        repo,
        content,
        args.mode,
        synthetic_installed=args.synthetic_installed_transition,
    )
    validate_post_expiry_partial_transition(
        repo,
        content,
        args.mode,
        synthetic_installed=args.synthetic_installed_transition,
    )
    validate_protected_transition_state(repo)
    partial_observation_paths, partial_observation_marker = validate_post_expiry_partial_state(repo, content)
    evidence_untracked = rehearsal_untracked | decision_untracked | failed_drupal_paths | failed_drupal_replacement_paths | final_failed_drupal_paths | drupal_replacement_paths | drupal_further_replacement_paths | partial_observation_paths
    validate_untracked_inventory(untracked, evidence_untracked, transition_untracked)
    staged = set(filter(None, git(repo, "diff", "--cached", "--name-only").splitlines()))
    require(not staged, "staged paths are prohibited during package audit")
    verify_step01_certification(repo)
    verify_path_hashes(repo, PROTECTED_SHA256, "protected Gate 2B local-only")
    verify_accepted_startup_evidence(repo)
    verify_quarantined_runtimes(repo, runtime_transition_ids)
    verify_historical_inventory_anchor(repo)
    validate_plan(content)
    validate_admission_anchor(content)
    validate_replacement_admission_anchor(content)
    validate_corrected_admission_anchor(content)
    validate_drupal_replacement_admission_anchor(content)
    validate_drupal_further_replacement_admission_anchor(content)
    validate_final_failed_governance(content)
    validate_post_expiry_partial_contract(content)
    validate_corrected_environment_evidence()
    verify_installed_sources(content)
    validate_architecture_decision_lifecycle_docs(content)
    scan_source(content)
    supervisor = (content / "scripts/gate2c_step02_supervisor.py").read_text(encoding="utf-8")
    require("signal.SIGKILL" in supervisor and "automatic_retry_count\": 0" in supervisor, "supervisor hard-termination/no-retry control")
    require("args.timeout == 30.0" in supervisor and "cleanup_is_not_experimental_sigkill" in supervisor, "bounded timeout/cleanup classification")
    require("BoundedStderr" in supervisor and "sanitize_diagnostic" in supervisor and "DIAGNOSTIC_LIMIT" in supervisor, "bounded redacted subprocess diagnostics")
    require('args.framework in {"crewai", "drupal_ai"}' in supervisor and '"worker_command_sha256"' in supervisor and '"stdout_capture": "DEVNULL_NOT_PERSISTED"' in supervisor, "Drupal durable pre-seam diagnostics")
    require("run_durable_checkpoint_verifier" in supervisor and supervisor.index("durable_checkpoint_id = validate_durable_checkpoint(") < supervisor.index("os.kill(actual_pid, signal.SIGKILL)"), "durable checkpoint validation before SIGKILL")
    require("run_drupal_process_check" in supervisor and "EXACT_SINGLETON_VERIFIED" in supervisor and "Drupal seam PID command identity mismatch" in supervisor and "Drupal replacement worker detected" in supervisor, "Drupal exact PID worker/no-replacement controls")
    require("durable_output" in supervisor and "DRUPAL_PROCESS_IDENTITY_SCAN" in supervisor and "bounded process-check candidates" in supervisor, "durable bounded Drupal process-scan evidence")
    require('["ddev", "exec", "kill", "-9", "{pid}"]' in supervisor and "EXACT_ACTUAL_PHP_WORKER_PID_ONLY" in supervisor, "Drupal exact PID SIGKILL scope")
    require("build_drupal_signal_dispatch_record" in supervisor and "persisted_before_wrapper_interpretation" in supervisor, "durable signal-dispatch evidence")
    require("validate_drupal_termination_evidence" in supervisor and "wrapper_status_is_not_inner_worker_signal_status" in supervisor and "NOT_REQUIRED_EXACT_WORKER_ABSENT" in supervisor, "inner-worker/wrapper/cleanup outcome separation")
    require(supervisor.index("write_json(args.signal_dispatch_output") < supervisor.index("post_kill_check = run_drupal_process_check") < supervisor.index("returncode = process.wait", supervisor.index("post_kill_check = run_drupal_process_check")), "post-signal durability ordering")
    langgraph = (content / "langchain/agentic_harness_langgraph/gate2c_recovery.py").read_text(encoding="utf-8")
    require('durability="sync"' in langgraph and "saver.get_tuple(config)" in langgraph, "LangGraph synchronous durability/public checkpoint readback")
    rehearsal = (content / "scripts/gate2c_step02_rehearsal.py").read_text(encoding="utf-8")
    require("sanitize_diagnostic" in rehearsal and "sanitized_stderr" in rehearsal, "sanitized failure diagnostics")
    require("authorize_offline" in rehearsal and "authorize_offline_replacement" in rehearsal and "authorize_offline_corrected_environment" in rehearsal and "load_one_run_authorization" in rehearsal, "pre-worker corrected-environment authorization boundary")
    require("finalize_offline_family" in rehearsal and "open_family_descriptors" in rehearsal, "post-cleanup complete-family finalization")
    require("derive_non_experimental_cleanup" in rehearsal and '"source": "SUPERVISOR_DIAGNOSTIC"' in rehearsal, "supervisor cleanup propagation")
    require('"outer_process_timed_out"' in rehearsal and '"supervisor_internal_timeout"' in rehearsal, "outer/supervisor timeout separation")
    require("record_post_inspection_addendum" in rehearsal and "POST_INSPECTION_NOT_EXPERIMENTAL_STATE" in rehearsal, "separate post-inspection provenance")
    require(rehearsal.index("load_one_run_authorization(repo, run_id)") < rehearsal.index("evidence.mkdir(parents=True)"), "authorization must precede family creation")
    require("finalize_offline_family(repo, run_id, outcome=\"PASS\")" in rehearsal and "finalize_offline_family(repo, run_id, outcome=outcome)" in rehearsal, "PASS/FAIL/TIMEOUT finalization paths")
    require("crewai_startup_diagnostic" in rehearsal and '"diagnose-startup"' in rehearsal, "separately authorized startup diagnostic")
    require("finalize_stack_location_diagnostic" in rehearsal and 'timeout_seconds=30.0' in rehearsal, "bounded stack diagnostic finalization")
    audit_source = (content / "scripts/gate2c_step02_audit.py").read_text(encoding="utf-8")
    require("validate_cleanup_classification" in audit_source and "expected_non_experimental_cleanup" in audit_source, "cleanup cross-record audit")
    require("KNOWN_HISTORICAL_CLASSIFICATION_INCONSISTENCY" in audit_source and LEGACY_CLASSIFICATION_RUN_ID in audit_source, "exact historical compatibility rule")
    crewai = (content / "crewai/agentic_harness_crewai/gate2c_recovery.py").read_text(encoding="utf-8")
    require("load_state" in crewai and "kickoff(inputs={\"id\": args.run_id})" in crewai, "CrewAI public candidate")
    require(all(token not in crewai for token in ("_restore_state", "_skip_auto_memory", "CheckpointConfig", "HumanFeedbackPending")), "prohibited CrewAI mechanism")
    require("from crewai.memory.storage.factory import set_memory_storage_factory" in crewai, "public CrewAI memory factory import")
    require("from .canonical_slice import RunScopedMemoryStorage" in crewai, "accepted Gate 2B memory backend import")
    require("class RunScopedMemoryStorage" not in crewai and all(token not in crewai for token in ("LanceDBStorage", "Qdrant", "qdrant")), "no replacement backend or built-in fallback")
    registration = "set_memory_storage_factory(lambda spec: memory_backend)"
    require(crewai.count(registration) == 1 and crewai.index(registration) < crewai.index("class Gate2CRehearsalFlow") < crewai.index("return Gate2CRehearsalFlow("), "memory factory registration ordering")
    require('require(not connection_trace.entered, "accepted memory factory fell back to lancedb.connect")' in crewai, "diagnostic LanceDB fallback rejection")
    require("validate_bootstrap_storage" in crewai and all(key in crewai for key in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME")), "CrewAI run-scoped XDG bootstrap validation")
    require("StartupPhaseReporter" in crewai and "target_6_midpoint_verified" in crewai and "seam_ready_emitted" in crewai, "CrewAI startup boundary reporting")
    require("ConnectionBoundaryTrace" in crewai and "sys.settrace" in crewai, "diagnostic-only LanceDB connection tracing")
    require("StackLocationProbe" in crewai and "sys._current_frames" in crewai, "standard-library function-location sampling")
    require("STACK_SNAPSHOT_DELAYS_SECONDS = (8.0, 18.0)" in crewai and "STACK_DEPTH_LIMIT = 12" in crewai, "bounded deterministic stack sampling")
    require("lancedb.background_loop import LOOP" in crewai and "LOOP.thread" in crewai, "exact LanceDB background-loop thread binding")
    require("MAIN_WORKER" in crewai and "LANCEDB_BACKGROUND_LOOP" in crewai, "bounded two-role stack sampling")
    require("lancedb.connect =" not in crewai and "setattr(lancedb" not in crewai, "LanceDB monkey patch is prohibited")
    require("frame.f_locals" not in crewai and "frame.f_globals" not in crewai, "diagnostic trace must not inspect frame data")
    require(all(token not in crewai for token in ("faulthandler", "traceback", "inspect.stack", "inspect.currentframe", "asyncio.all_tasks", "get_stack(", "call_soon_threadsafe")), "unfiltered or event-loop-interfering capture is prohibited")
    require("classify_connection_boundary" in supervisor and "LANCEDB_CONNECT_ENTERED_NO_RETURN" in supervisor, "connection-boundary fail-closed classification")
    require("FLOW_CONSTRUCTION_COMPLETED_WITHOUT_LANCEDB_CONNECT" in supervisor, "accepted memory-factory completion classification")
    require("import_crewai_runtime" in crewai and crewai.index("crewai_import_started") < crewai.index("from crewai.flow import Flow"), "CrewAI import boundary reporting")
    require("crewai_bootstrap_env" in rehearsal and "CREWAI_STORAGE_DIR" in rehearsal and "CREWAI_DISABLE_VERSION_CHECK" in rehearsal, "CrewAI bootstrap environment binding")
    require('env["CREWAI_DISABLE_TELEMETRY"] = "true"' in rehearsal, "CrewAI child telemetry disable control")
    require("CREWAI_DISABLE_TRACKING" not in rehearsal and "OTEL_SDK_DISABLED" not in rehearsal, "CrewAI telemetry control is not the minimal supported selection")
    for relative in PINNED_CREWAI_TELEMETRY_SOURCES:
        telemetry = (repo / relative).read_text(encoding="utf-8")
        require(
            'os.getenv("CREWAI_DISABLE_TELEMETRY", "false").lower() == "true"' in telemetry,
            f"pinned CrewAI telemetry disable semantics: {relative}",
        )
        guard_offset = telemetry.index("if self._is_telemetry_disabled():")
        require(
            guard_offset < telemetry.index("SafeOTLPSpanExporter(", guard_offset),
            f"pinned CrewAI telemetry check must precede exporter construction: {relative}",
        )
    require('CREWAI_WORKER_MODULE = "agentic_harness_crewai.gate2c_recovery"' in rehearsal, "CrewAI package module identity")
    require('return [str(python), "-m", CREWAI_WORKER_MODULE]' in rehearsal, "CrewAI package-aware module command")
    require('env["PYTHONPATH"] = str(package_root)' in rehearsal, "CrewAI subprocess-scoped package root")
    require('repo=repo, env=crewai_bootstrap_env(control, repo / "crewai")' in rehearsal, "startup diagnostic repository working directory and package path")
    require("natural lock expiry has not elapsed; this command never waits" in rehearsal, "Drupal post-expiry command must not wait or poll")
    require("immediate post-kill observation required before post-expiry invocation" in rehearsal, "Drupal phase order")
    require("drupal_post_expiry_partial" in rehearsal and "validate_post_expiry_partial_result" in rehearsal, "separately governed partial-observation controller")
    require("recorded natural expiry has not elapsed; this command never waits" in rehearsal, "partial observation must not wait or poll")
    require('run_id == FINAL_FAILED_DRUPAL_RUN_ID' in rehearsal and '"worker_launch_count": 0' in rehearsal, "partial observation exact identity/no-worker boundary")
    require("replacement_worker_count" in rehearsal and "process-check-command.json" in rehearsal, "Drupal replacement-worker binding")
    require("drupal_script_command" in rehearsal and '"--diagnostic-output"' in rehearsal, "Drupal exact command and diagnostic binding")
    require("authorize_drupal_replacement" in rehearsal and "load_drupal_replacement_authorization" in rehearsal, "Drupal replacement admission mechanism")
    require("authorize_drupal_further_replacement" in rehearsal and "load_drupal_further_replacement_authorization" in rehearsal, "Drupal further replacement admission mechanism")
    require('"repaired_installed_source_manifest_sha256": sha(repo / INSTALLED_SOURCE_MANIFEST)' in rehearsal and 'value.get("repaired_installed_source_manifest_sha256") == sha(repo / INSTALLED_SOURCE_MANIFEST)' in rehearsal, "future Drupal replacement allocation/current epoch binding")
    require('repo / "crewai/agentic_harness_crewai/gate2c_recovery.py"' not in rehearsal, "direct CrewAI worker file invocation remains")
    require("lancedb_async_diagnostic" in rehearsal and 'timeout_seconds=30.0' in rehearsal, "bounded public async differential diagnostic")
    require('"public_connect_async_calls": 1' in rehearsal and '"automatic_retry_count": 0' in rehearsal, "one-attempt/no-retry async diagnostic")
    require("lancedb_memory_async_diagnostic" in rehearsal and 'root_name="lancedb-memory-async"' in rehearsal, "bounded public in-memory async differential diagnostic")
    require('"IN_MEMORY_ASYNC_CONNECT_TIMEOUT"' in rehearsal and '"filesystem_storage_created": False' in rehearsal, "in-memory classifications and filesystem boundary")
    async_worker = (content / "crewai/agentic_harness_crewai/gate2c_lancedb_async_diagnostic.py").read_text(encoding="utf-8")
    require("asyncio.run" in async_worker and 'module_loader("lancedb")' in async_worker, "caller-owned public LanceDB async path")
    require("await connect_async(str(storage))" in async_worker, "exact one public connect_async call")
    require("import crewai" not in async_worker and "from crewai" not in async_worker, "async diagnostic imports CrewAI")
    require("lancedb.connect(" not in async_worker and "BackgroundEventLoop" not in async_worker and "LOOP.run" not in async_worker, "async diagnostic uses synchronous bridge")
    require(all(token not in async_worker for token in ("asyncio.all_tasks", "get_stack(", "call_soon_threadsafe", "traceback", "faulthandler")), "async diagnostic task or traceback introspection")
    memory_async_worker = (content / "crewai/agentic_harness_crewai/gate2c_lancedb_memory_async_diagnostic.py").read_text(encoding="utf-8")
    require("asyncio.run" in memory_async_worker and 'module_loader("lancedb")' in memory_async_worker, "caller-owned public LanceDB in-memory async path")
    require('await connect_async(MEMORY_URI)' in memory_async_worker and 'MEMORY_URI = "memory://"' in memory_async_worker, "exact one public memory connect_async call")
    require("import crewai" not in memory_async_worker and "from crewai" not in memory_async_worker, "in-memory diagnostic imports CrewAI")
    require("lancedb.connect(" not in memory_async_worker and "BackgroundEventLoop" not in memory_async_worker and "LOOP.run" not in memory_async_worker, "in-memory diagnostic uses synchronous bridge")
    require(all(token not in memory_async_worker for token in ("asyncio.all_tasks", "get_stack(", "call_soon_threadsafe", "traceback", "faulthandler")), "in-memory diagnostic task or traceback introspection")
    runner = (content / "scripts/run-gate2c-step02-shared-failure-injector-and-model-free-rehearsals.sh").read_text(encoding="utf-8")
    require("GATE2C_STEP02_ONE_RUN_ADMISSION_AUTHORIZED" in runner and "one-offline-rehearsal-identity-admission" in runner, "one-run admission authorization guard")
    require("GATE2C_STEP02_REPLACEMENT_ADMISSION_AUTHORIZED" in runner and "one-fresh-offline-rehearsal-replacement-identity" in runner, "one-run replacement authorization guard")
    require("GATE2C_STEP02_CORRECTED_ENVIRONMENT_ADMISSION_AUTHORIZED" in runner and "one-corrected-environment-offline-rehearsal-identity" in runner, "corrected-environment admission authorization guard")
    require(runner.count('safe_python "$corrected_preflight" --result') == 2 and "GATE2C_CODEX_SANDBOX_MODE" in runner and "danger-full-access" in runner, "corrected-environment preflight and Codex sandbox guard")
    require("GATE2C_STEP02_POST_INSPECTION_AUTHORIZED" in runner and "classify-post-inspection-artifacts-separately" in runner, "post-inspection authorization guard")
    require("GATE2C_STEP02_LANCEDB_ASYNC_DIAGNOSTIC_AUTHORIZED" in runner and "one-disposable-public-lancedb-async-connect-diagnostic" in runner, "async diagnostic authorization guard")
    require("GATE2C_STEP02_LANCEDB_MEMORY_ASYNC_DIAGNOSTIC_AUTHORIZED" in runner and "one-disposable-public-lancedb-memory-async-connect-diagnostic" in runner, "in-memory diagnostic authorization guard")
    for token in (
        "GATE2C_STEP02_DRUPAL_REPLACEMENT_ADMISSION_AUTHORIZED",
        "GATE2C_STEP02_DRUPAL_REPLACEMENT_START_AUTHORIZED",
        "GATE2C_STEP02_DRUPAL_IMMEDIATE_AUTHORIZED",
        "GATE2C_STEP02_DRUPAL_POST_EXPIRY_AUTHORIZED",
        "GATE2C_STEP02_DRUPAL_POST_EXPIRY_PARTIAL_AUTHORIZED",
        "GATE2C_STEP02_DRUPAL_FINALIZE_AUTHORIZED",
        "GATE2C_STEP02_RESET_REHEARSAL_AUTHORIZED",
        "GATE2C_STEP02_CERTIFICATION_AUTHORIZED",
    ):
        require(token in runner, f"separate lifecycle authorization guard: {token}")
    drupal = (content / "drupal/scripts/gate2c-step02-drupal-rehearsal.php").read_text(encoding="utf-8")
    require("gate2c_step02_normalize_drush_extra" in drupal and "$extra ?? NULL" in drupal and "$argv" not in drupal, "Drush-supported Drupal argument interface")
    require("GATE2C_STEP02_LOCK_LEASE = 1800.0" in drupal, "Drupal lease drift")
    require("gate2c_step02_post_expiry_partial" in drupal and "GATE2C_STEP02_PARTIAL_PROBE_LEASE = 1.0" in drupal, "bounded partial-observation lock probe")
    require("PASS_PARTIAL_POST_NATURAL_EXPIRY_NON_CERTIFYING" in drupal and "certifying_evidence' => FALSE" in drupal, "partial observation non-certifying semantics")
    require(all(token not in drupal for token in ("lock->delete", "lock->clear", "lock->wait")), "Drupal lock mutation/bypass")
    require("lock_expires_not_before_unix" in drupal and "elapsed_since_lock_acquired_seconds" in drupal, "Drupal natural-expiry chronology")
    require("gate2c_step02_process_check" in drupal and "matching_worker_pids" in drupal, "Drupal exact process identity check")
    require("pid_namespace_matches_observer" in drupal and "exact_worker_identity" in drupal and "observer_pid" in drupal, "Drupal exact PID namespace/mode/self-observer classification")
    reset = (content / "scripts/gate2c_step02_reset_rehearsal.py").read_text(encoding="utf-8")
    require("require_finalized_drupal_evidence" in reset and "--drupal-run-id" in reset, "reset requires finalized Drupal lifecycle evidence")
    require('"privacy-scan.json"' in reset and '"summary.md"' in reset and '"automatic_certification": False' in reset, "reset complete evidence/no-promotion controls")
    certify = (content / "scripts/gate2c_step02_certify.py").read_text(encoding="utf-8")
    require("Drupal natural expiry duration" in certify and "reset Drupal manifest binding" in certify, "certification Drupal/reset chronology binding")
    if args.evidence:
        evidence = args.evidence.resolve()
        require(evidence.is_dir(), "evidence directory missing")
        expected = {"certification.json", "predecessor-bindings.json", "rehearsal-bindings.json", "authorization-ledger.json", "privacy-scan.json", "summary.md", "evidence-manifest.json"}
        require({path.name for path in evidence.iterdir() if path.is_file()} == expected, "certification evidence file set")
        scan_evidence(evidence)
        verify_manifest(evidence)
        certification = json.loads((evidence / "certification.json").read_text(encoding="utf-8"))
        require(certification.get("status") == "PASS" and certification.get("contract_sha256") == CONTRACT_SHA, "certification binding")
        require(certification.get("model_free") is True and certification.get("authoritative_experiment_executed") is False, "certification operation boundary")
        bindings = json.loads((evidence / "rehearsal-bindings.json").read_text(encoding="utf-8"))["bindings"]
        require([item["label"] for item in bindings] == ["offline", "drupal", "reset", "crewai_human_decision"], "rehearsal binding order/set")
        from gate2c_step02_certify import validate_drupal, validate_offline, validate_reset
        validators = {"offline": validate_offline, "drupal": validate_drupal, "reset": validate_reset}
        for item in bindings[:3]:
            root = (repo / item["path"]).resolve()
            require(root.is_relative_to(repo), "bound evidence outside repository")
            require(sha(root / "evidence-manifest.json") == item["manifest_sha256"], f"{item['label']} manifest binding")
            validators[item["label"]](root)
        decision = (repo / bindings[3]["path"]).resolve()
        require(decision.is_relative_to(repo) and sha(decision) == bindings[3]["sha256"], "CrewAI decision binding")
        decision_value = json.loads(decision.read_text(encoding="utf-8"))
        require(decision_value.get("human_decision") == "APPROVED" and decision_value.get("decided_by") == "human_operator", "CrewAI human decision")
        status = (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8")
        require("Steps 2C.01 and 2C.02 are complete" in status and "no authoritative experiment has run" in status, "Step 2C.02 lifecycle status")
    print("[PASS] Gate 2C.01 certification evidence, contract, predecessor freezes, snapshot, and eleven protected path hashes")
    require(len(QUARANTINED_FAILED_ATTEMPTS) == 11, "quarantined failed-family count")
    require(sum(len(value) for value in QUARANTINED_FAILED_ATTEMPTS.values()) == 34, "quarantined evidence count")
    require(sum(len(value) for value in QUARANTINED_RUNTIME_ARTIFACTS.values()) == 63, "original quarantined runtime artifact count")
    require(sum(len(value) for value in POST_INSPECTION_RUNTIME_ARTIFACTS.values()) == 4, "post-inspection runtime artifact count")
    require(len(ACCEPTED_STARTUP_EVIDENCE) == 5 and len(ACCEPTED_STARTUP_RUNTIME) == 4, "accepted startup family count")
    print("[PASS] twelve retained families: thirty-nine evidence files, sixty-seven original runtime artifacts, and four separately classified post-inspection SQLite sidecars are exact")
    print("[PASS] the four post-inspection sidecars are raw-byte/size bound and are not classified as at-timeout experimental evidence")
    require(len(INSTALLED_SOURCES) == 39, "installed source inventory count")
    if corrected_id is None:
        transition_status = "EMPTY_SINGLE_USE_CORRECTED_ENVIRONMENT_SLOT"
    elif corrected_id not in runtime_transition_ids:
        transition_status = "CORRECTED_ENVIRONMENT_AUTHORIZED_NOT_STARTED"
    else:
        transition_status = "ONE_CORRECTED_ENVIRONMENT_FAMILY_FINALIZED_AND_HASH_BOUND"
    print(f"[PASS] corrected-environment admission transition status: {transition_status}")
    print("[PASS] historical rehearsal source epoch 8a74aa96... remains exact and distinct from later governance/source epochs; current files match the selected installed-source manifest")
    print(f"[PASS] exact 851b9224... failed-start repair predecessor and sealed successor transition: {args.mode.upper()}")
    print("[PASS] the exact governance-only v1.0.0/v1.0.2 transition, protected 366-file state including all three failed Drupal evidence families, and seven-LATEST aggregate fingerprint remain exact")
    print("[PASS] exactly one schema-valid human APPROVED CrewAI architecture decision is bound to the exact corrected-environment authorization, both preflights, finalized PASS, source manifest, and complete diagnostic/environment history")
    print("[PASS] thirty-nine exact Step 2C.02 source hashes, three immutable failed Drupal families, corrected offline PASS, CrewAI human approval, no-retry, privacy, and separate lifecycle authorization guards")
    print("DRUPAL_START_FAILED_PRESERVED")
    print("DRUPAL_REPLACEMENT_START_PROCESS_IDENTITY_FAILED_PRESERVED")
    print("DRUPAL_FURTHER_REPLACEMENT_START_POST_SIGKILL_TERMINATION_PROOF_FAILED_PRESERVED")
    print("DRUPAL_IMMEDIATE_OBSERVATION_MISSED_DUE_TO_TERMINATION_PROOF_GATE")
    print(partial_observation_marker)
    print("RESET_NOT_PERFORMED")
    print("STEP_2C_02_UNCERTIFIED")
    print("STEP_2C_02_SOURCE_AUDIT_PASS")
    print("CREWAI_RECOVERY_ARCHITECTURE_HUMAN_APPROVED_STEP_2C_02_UNCERTIFIED")
    print("GATE_2C_DEFERRED_UNCLAIMED")
    print("GATE_2_NOT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
