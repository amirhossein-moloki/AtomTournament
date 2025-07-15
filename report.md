# Technical Audit Report

This report outlines the findings of a technical audit of the tournament project.

## Summary of Findings

The project exhibits several significant flaws in its structure, documentation, and code quality. While some refactoring has been done, the project is not in a satisfactory state. The test suite is inadequate and provides a false sense of security. The documentation is outdated and misleading.

## Specific Issues

1.  **Committed Artifacts:** The repository contains committed artifacts, including `.env` files, `db.sqlite3`, `__pycache__` directories, and `*.pyc` files. This is a security risk and a violation of best practices. These files have been removed from the git index.
2.  **Outdated and Inaccurate Documentation:** The `reports.md` file was outdated and contained misleading information. It has been deleted. The `report.md` file contained inaccurate claims about the state of the project, which have been corrected.
3.  **Inadequate Test Coverage:** The test suite is not comprehensive and contains several flaws.
    *   The tests primarily focus on the happy path and do not cover edge cases or failure scenarios.
    *   A test in `tournaments/tests.py` was a placeholder with no assertions and has been removed.
    *   Tests in `users/tests.py` contained incorrect assertions and have been fixed.
4.  **Model Design Flaws:**
    *   The `InGameID` model in the `users` app has a nullable `ForeignKey` to `User`, which can lead to data integrity issues.
    *   The `Match` model in the `tournaments` app uses multiple nullable `ForeignKey` fields to represent participants, which is a complex and error-prone design.
5.  **Security Concerns:**
    *   The `result_proof` field in the `Match` model uploads files to a "private" directory, but there is no evidence of access control, which could expose sensitive information.

## Conclusion

The project requires significant work to meet enterprise-grade standards. The issues identified in this report should be addressed to improve the project's quality, security, and maintainability.

## Detailed Findings

### 1. Vendored Dependencies

The project includes a vendored (copied directly into the source code) version of the `django-ratelimit` library. This is a critical anti-pattern for the following reasons:

*   **Inconsistent Versioning:** The `requirements.txt` file specifies `django-ratelimit==4.0.0`, while the vendored version is `4.1.0`, as evidenced by the `django_ratelimit-4.1.0.dist-info` directory. This discrepancy makes it impossible to determine which version is actually in use and creates a significant risk of unexpected behavior.
*   **Inability to Patch:** Vendored dependencies do not receive security updates or bug fixes from the original author. The project is permanently stuck on an outdated version of the library, exposing it to any vulnerabilities that have been discovered since its release.
*   **Increased Maintenance Burden:** The project is now responsible for maintaining the vendored code, which is a significant and unnecessary burden.
*   **Violation of Best Practices:** This practice violates the principle of separation of concerns and makes the project difficult to manage and deploy.

### 2. Model Design Flaws

The data models exhibit several critical design flaws that compromise data integrity and create unnecessary complexity.

#### `tournaments.Match` Model

The `Match` model uses six nullable `ForeignKey` fields (`participant1_user`, `participant2_user`, `participant1_team`, `participant2_team`, `winner_user`, `winner_team`) to represent participants and winners. This is a fundamentally flawed design:

*   **Data Integrity:** The use of nullable foreign keys makes it possible to create records in an inconsistent state (e.g., a match with a user participant and a team participant). The `clean` method attempts to mitigate this, but it is a-posteriori validation and does not prevent inconsistent data at the database level.
*   **Querying Complexity:** This design makes it extremely difficult to write clear, efficient queries. For example, retrieving all matches for a specific user requires querying two different fields (`participant1_user` and `participant2_user`).
*   **Scalability:** The design is not scalable. If a new participant type were to be introduced (e.g., a "clan"), the model would require significant modification.

A more robust solution would use a generic `ForeignKey` to a `Participant` model, which could then be linked to a `User` or `Team` via a `GenericForeignKey` or a similar mechanism.

#### `users.InGameID` Model

The `InGameID` model has a nullable `ForeignKey` to the `User` model. This is a critical flaw. An in-game ID that is not associated with a user is meaningless data. The `null=True` attribute on the `user` field should be removed to enforce data integrity at the database level.

### 3. Security Configurations

The project has some security measures in place, but they are not consistently applied and, in some cases, are misleading.

#### `django-cors-headers`

The `CORS_ALLOWED_ORIGINS` setting is configured to allow requests from `http://localhost:3000`. While this is acceptable for local development, it is insecure for a production environment. This setting must be updated to a restrictive list of trusted domains before deployment.

#### "Private" File Uploads

The `PRIVATE_MEDIA_ROOT` setting and the `upload_to="private_result_proofs/"` argument in the `Match.result_proof` field are misleading. There is no evidence of any access control mechanism to protect these files. Any file uploaded to this directory is publicly accessible if the `MEDIA_URL` is served. This is a critical security vulnerability that could expose sensitive information.

#### Security Headers

The project has correctly configured several security headers, including `X-XSS-Protection`, `X-Content-Type-Options`, `Strict-Transport-Security`, and secure cookies. This is a positive finding.

#### `django-axes`

The `django-axes` library is configured with a failure limit of 5 attempts and a cool-off period of 1 hour. This provides a reasonable level of protection against brute-force authentication attacks.

### 4. Inadequate Test Suite

The test suite is superficial and provides a false sense of security. The tests primarily focus on the "happy path" and fail to cover critical failure scenarios and edge cases.

#### `tournaments/tests.py`

*   **Lack of Failure Case Testing:** The tests for joining a tournament do not cover scenarios such as a user with insufficient funds or a user attempting to join a team tournament without being a member of a team.
*   **Insufficient Permissions Testing:** The `test_generate_matches` test circumvents the permissions system by manually setting `is_staff = True` on the user object. This is not a valid test of the actual permission checks.
*   **Missing Model Validation Tests:** There are no tests to verify that the `Match` model's `clean` method correctly prevents the creation of matches with inconsistent participant types.

#### `users/tests.py`

*   **Incomplete User Validation Testing:** The tests for user creation do not cover all validation rules, such as the format of the phone number.
*   **Superficial Team Management Tests:** The tests for team management do not cover edge cases, such as attempting to remove the captain of a team or transferring captaincy.
*   **Missing `InGameID` Constraint Tests:** There are no tests to verify the `unique_together` constraint on the `InGameID` model, which is a critical data integrity rule.
