# Contract Test Fixtures

This directory contains API contract files for testing Forseti's contract validation and compatibility checking functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `provider_v1.yaml` | Initial API version (User Service) | Baseline contract |
| `provider_v2_compatible.yaml` | Backward-compatible changes | Compatible evolution testing |
| `provider_v2_breaking.yaml` | Breaking changes | Breaking change detection |
| `consumer_contract.yaml` | Consumer expectations (Order Service) | Consumer-driven testing |

## Contract Evolution

### provider_v1.yaml (Baseline)

The initial User Service API contract:

**Endpoints:**
- `GET /users` - List users (paginated)
- `POST /users` - Create user
- `GET /users/{userId}` - Get user by ID
- `PUT /users/{userId}` - Update user
- `DELETE /users/{userId}` - Delete user
- `GET /users/{userId}/profile` - Get user profile

**User Schema:**
```yaml
User:
  required: [id, email, name, role, status, createdAt]
  properties:
    id: uuid
    email: email
    name: string (1-100)
    role: enum [user, admin, moderator]
    status: enum [active, inactive, pending]
```

### provider_v2_compatible.yaml (Backward Compatible)

Changes that maintain backward compatibility:

| Change Type | Description | Compatibility |
|-------------|-------------|---------------|
| Added optional field | `phone` in User | Compatible |
| Added optional field | `website` in UserProfile | Compatible |
| Added enum value | `guest` role | Compatible |
| Added new endpoint | `/users/{userId}/preferences` | Compatible |
| Added optional parameter | `role` filter in list | Compatible |
| Relaxed constraint | `bio` maxLength 500 -> 1000 | Compatible |
| Added optional field | `metadata` in User | Compatible |

**Compatibility Level:** BACKWARD (existing consumers unaffected)

### provider_v2_breaking.yaml (Breaking Changes)

Changes that break existing consumers:

| Change Type | Description | Breaking Reason |
|-------------|-------------|-----------------|
| Removed endpoint | `/users/{userId}/profile` | Consumers depend on it |
| Removed enum value | `moderator` role | Existing data invalid |
| Renamed field | `name` -> `fullName` | Consumers expect `name` |
| Changed field type | `status`: string -> object | Different structure |
| Added required field | `organizationId` in CreateUser | Existing requests fail |
| Changed parameter type | `userId`: uuid -> integer | Type mismatch |
| Removed field | `password` from CreateUser | Workflow broken |
| Changed HTTP method | PUT -> PATCH for update | Client changes needed |
| Changed response structure | `data` -> `users` | Parsing fails |

**Compatibility Level:** NONE (breaking changes detected)

### consumer_contract.yaml (Consumer-Driven)

Order Service's expectations from User Service:

**Required Operations:**
1. `getUser` - Validate user exists before order
2. `validateUser` - Check user eligibility for ordering

**Expected Fields:**
```yaml
UserResponse:
  required: [id, email, name, status]
  # Consumer only needs these fields
  # Additional provider fields are acceptable
```

**Contract Tests (x-contract-tests):**
```yaml
- name: Get active user
  request:
    method: GET
    path: /users/{userId}
  expected_response:
    status: 200
    body_contains: [id, email, name, status]

- name: Get non-existent user
  expected_response:
    status: 404
```

## Usage Examples

### Compatibility Checking

```python
from Asgard.Forseti.Contracts.services.compatibility_checker_service import CompatibilityCheckerService

checker = CompatibilityCheckerService()

# Check backward compatibility
result = checker.check_compatibility(
    "provider_v1.yaml",
    "provider_v2_compatible.yaml"
)
assert result.is_compatible
assert result.compatibility_level == "backward"
assert len(result.breaking_changes) == 0

# Check breaking changes
result = checker.check_compatibility(
    "provider_v1.yaml",
    "provider_v2_breaking.yaml"
)
assert not result.is_compatible
assert len(result.breaking_changes) > 0

for change in result.breaking_changes:
    print(f"{change.change_type}: {change.message}")
```

### Consumer Contract Validation

```python
from Asgard.Forseti.Contracts.services.contract_validator_service import ContractValidatorService

validator = ContractValidatorService()

# Validate provider implements consumer contract
result = validator.validate_contract(
    consumer_contract="consumer_contract.yaml",
    provider_spec="provider_v1.yaml"
)
assert result.is_valid

# Breaking version fails consumer contract
result = validator.validate_contract(
    consumer_contract="consumer_contract.yaml",
    provider_spec="provider_v2_breaking.yaml"
)
assert not result.is_valid
# Missing: /users/{userId}/profile endpoint (if consumer expected it)
```

### Breaking Change Detection

```python
from Asgard.Forseti.Contracts.services.breaking_change_detector_service import BreakingChangeDetectorService

detector = BreakingChangeDetectorService()

changes = detector.detect_breaking_changes(
    "provider_v1.yaml",
    "provider_v2_breaking.yaml"
)

for change in changes:
    print(f"[{change.change_type}] {change.path}")
    print(f"  Old: {change.old_value}")
    print(f"  New: {change.new_value}")
    print(f"  Mitigation: {change.mitigation}")
```

## Breaking Change Types

The `BreakingChangeType` enum covers:

| Type | Description |
|------|-------------|
| `REMOVED_ENDPOINT` | Endpoint no longer exists |
| `REMOVED_FIELD` | Required response field removed |
| `REMOVED_ENUM_VALUE` | Enum value no longer valid |
| `CHANGED_TYPE` | Field type changed |
| `CHANGED_REQUIRED` | Optional field became required |
| `NARROWED_TYPE` | Type constraints tightened |
| `REMOVED_PARAMETER` | Query/path parameter removed |
| `ADDED_REQUIRED_PARAMETER` | New required parameter |
| `CHANGED_PATH` | Endpoint path changed |
| `CHANGED_METHOD` | HTTP method changed |
| `REMOVED_RESPONSE` | Response status code removed |
| `CHANGED_RESPONSE_TYPE` | Response content type changed |

## Testing Scenarios

1. **Full Compatibility**: v1 vs v2_compatible should show no breaking changes
2. **Breaking Detection**: v1 vs v2_breaking should detect all issues
3. **Consumer Validation**: consumer_contract vs provider specs
4. **Semantic Versioning**: Suggest major version bump for breaking changes
5. **Migration Guidance**: Generate migration guide from detected changes
