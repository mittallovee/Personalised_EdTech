// Generated from api/openapi.json by `pnpm --filter @qbank/api-client generate`. Do not edit.

export interface paths {
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Process is running */
        get: operations["live_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready to serve: database reachable and schema up to date */
        get: operations["ready_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign in with email and password */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/links/redeem": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Activate an account or reset its password with a one-time link
         * @description For people who are not signed in (no session or CSRF token needed): the token from the link and a new password. On success the person is signed in, exactly as after `POST /auth/login`. A reset ends all their other sessions. Rate-limited like sign-in.
         */
        post: operations["redeem_link_api_v1_auth_links_redeem_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign out */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The signed-in user */
        get: operations["me_api_v1_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/methods": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Which sign-in methods are on
         * @description For the sign-in page: hides the Google button while Google is not set up.
         */
        get: operations["auth_methods_api_v1_auth_methods_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start signing in with Google
         * @description Returns the Google address to send the browser to, and sets a short-lived HttpOnly cookie that only this browser can finish the flow with. Nothing is created: signing in works only for a Google account somebody already linked.
         */
        post: operations["start_google_api_v1_auth_google_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/start-activation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start activating an account with Google
         * @description Like `POST /auth/google/start`, for a person who has an activation link and would rather use Google than set a password. The link is checked before leaving for Google, and again when Google calls back; the Google account is then bound to the person the link was made for. Nothing else is ever created.
         */
        post: operations["start_google_activation_api_v1_auth_google_start_activation_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/start-link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start linking a Google account to my account
         * @description For a signed-in person with a password. The current password must be in this very request: a session alone is never enough. Wrong passwords count towards the sign-in lockout. Returns the Google address to send the browser to; when Google calls back, the account is linked (the session stays as it is). Only one Google account can be linked.
         */
        post: operations["start_google_link_api_v1_auth_google_start_link_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/unlink": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Unlink my Google account */
        post: operations["unlink_google_api_v1_auth_google_unlink_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/login-methods": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * How I can sign in
         * @description Whether the signed-in account has a password and a linked Google account.
         */
        get: operations["my_login_methods_api_v1_me_login_methods_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Where Google sends the browser back
         * @description Not called by our web app. On success the browser is redirected to the home page with a new session, as after `POST /auth/login`; for linking, to `/profile?google=linked`. Every failure (an unknown or replayed flow, a Google account nobody linked or already linked, no access any more, Google refusing) is the same redirect, to `/login?google=failed` (to `/profile?google=failed` when linking, to `/activate?google=failed` when activating), so nothing is revealed.
         */
        get: operations["google_callback_api_v1_auth_google_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/audit-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Audit log: who changed what, and when (I-03)
         * @description Owner and admins see their coaching's events. A platform admin sees the coaching they act in, or platform-level events when not acting in one. Newest first.
         */
        get: operations["list_audit_events_api_v1_audit_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platform/organizations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** All coachings, newest first */
        get: operations["list_organizations_api_v1_platform_organizations_get"];
        put?: never;
        /**
         * Create a coaching and invite its first Owner (A-04)
         * @description Creates the coaching, the Owner's account (invited: it cannot sign in yet) and a one-time activation link valid for 24 hours. Send an `Idempotency-Key` so a retry after a lost response returns the same coaching (with a fresh link) instead of failing.
         */
        post: operations["create_organization_api_v1_platform_organizations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platform/organizations/{organization_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One coaching */
        get: operations["get_organization_api_v1_platform_organizations__organization_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Rename a coaching or change its time zone
         * @description Send the ETag from your last read in `If-Match`. Only the fields sent change.
         */
        patch: operations["update_organization_api_v1_platform_organizations__organization_id__patch"];
        trace?: never;
    };
    "/api/v1/platform/organizations/{organization_id}/suspend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Suspend a coaching (A-07)
         * @description Ends its members' sign-in sessions; they cannot sign in until it is reactivated, and its data is kept. Send the ETag in `If-Match`. Suspending a suspended coaching changes nothing.
         */
        post: operations["suspend_organization_api_v1_platform_organizations__organization_id__suspend_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platform/organizations/{organization_id}/reactivate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reactivate a suspended coaching
         * @description Members sign in again. Send the ETag in `If-Match`.
         */
        post: operations["reactivate_organization_api_v1_platform_organizations__organization_id__reactivate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platform/acting-organization": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Act inside a coaching (A-06)
         * @description Until stopped or signed out, this sign-in session works inside that coaching with full authority. Changes are audited as made by a platform admin, and starting and stopping appear in the coaching's audit log. `/me` shows the coaching acted in.
         */
        post: operations["start_acting_api_v1_platform_acting_organization_post"];
        /** Stop acting inside a coaching */
        delete: operations["stop_acting_api_v1_platform_acting_organization_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Members of your coaching, newest first
         * @description Owner and admins (and a platform admin acting in the coaching). Removed members are left out.
         */
        get: operations["list_members_api_v1_members_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One member
         * @description The ETag is the member's revision, for changes that need `If-Match`.
         */
        get: operations["get_member_api_v1_members__membership_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/invitations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Invite an admin or faculty member (B-05)
         * @description Creates their account (invited: it cannot sign in yet) and a one-time activation link valid for 24 hours, for you to send them. Admins invite faculty; only the Owner invites admins. Send an `Idempotency-Key` so a retry after a lost response returns the same member (with a fresh link) instead of failing.
         */
        post: operations["invite_member_api_v1_members_invitations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}/activation-link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * New activation link for someone who has not activated yet
         * @description Valid for 24 hours; their earlier activation link stops working.
         */
        post: operations["new_activation_link_api_v1_members__membership_id__activation_link_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}/reset-link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Password-reset link for an active account
         * @description Valid for 1 hour; using it sets a new password and signs the person out everywhere else. Admins make links for faculty, the Owner for admins too; the Owner's own link comes from a platform admin.
         */
        post: operations["new_reset_link_api_v1_members__membership_id__reset_link_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}/grants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Set a faculty member's grants (B-09)
         * @description Replaces their grants with the list sent (QC, APPROVE, PUBLISH, EDIT_OTHERS, MANAGE_AI_PROMPTS). Owner and admins may do this. Send the ETag from your last read in `If-Match`. The change applies from the member's next request.
         */
        put: operations["set_grants_api_v1_members__membership_id__grants_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}/change-role": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Promote faculty to admin, or demote an admin to faculty (B-08)
         * @description Owner only. Name the role you saw in `expected_role` and send the ETag from your last read in `If-Match`; if either is out of date nothing changes. Their grants are cleared (admins hold every grant anyway). The new role applies from their next request. The Owner changes only by a transfer of ownership.
         */
        post: operations["change_role_api_v1_members__membership_id__change_role_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/{membership_id}/remove": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Remove someone from the coaching (B-08, B-09, B-10)
         * @description Owner and admins remove faculty; only the Owner removes admins. Their sign-in sessions and unused links end at once; their content and history stay with the coaching. If they never activated, their email is freed. Name the role you saw in `expected_role` and send the ETag in `If-Match`. The Owner can't be removed.
         */
        post: operations["remove_member_api_v1_members__membership_id__remove_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/organization/transfer-ownership": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Hand the coaching to another admin (B-08)
         * @description The Owner (or a platform admin acting in the coaching) makes an admin of this coaching the Owner; the old Owner becomes an admin. Name the Owner you saw in `expected_owner_membership_id` and send that Owner's ETag (from `GET /members/{id}`) in `If-Match`; if either is out of date nothing changes. The new Owner must be an admin who has activated their account. The change applies from each person's next request.
         */
        post: operations["transfer_ownership_api_v1_organization_transfer_ownership_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/languages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The question languages
         * @description The same for every coaching. English comes first. Like the syllabus, they are for people in a coaching (or a platform admin acting in one).
         */
        get: operations["list_languages_api_v1_languages_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalogues/bloom": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** The Bloom levels, easiest first */
        get: operations["list_bloom_levels_api_v1_catalogues_bloom_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalogues/difficulty-guide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * What each difficulty level from 1 to 10 means
         * @description Shown beside the difficulty field of the question editor.
         */
        get: operations["difficulty_guide_api_v1_catalogues_difficulty_guide_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/nodes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Syllabus items, in the admin's order
         * @description Everyone in the coaching can read them. Filter by `kind` and by `parent_id` (the items directly under one item). Retired items are included unless you ask for `state=ACTIVE`, which is what a picker for a new question should do.
         */
        get: operations["list_nodes_api_v1_taxonomy_nodes_get"];
        put?: never;
        /**
         * Add a syllabus item
         * @description Owner and admins. A subject goes under a class, a chapter under a subject, a topic under a chapter and a subtopic under a topic; a class has no parent. Send an `Idempotency-Key` so a retry after a lost response returns the same item instead of failing.
         */
        post: operations["create_node_api_v1_taxonomy_nodes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/nodes/{node_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One syllabus item
         * @description The ETag is its revision, for changes that need `If-Match`.
         */
        get: operations["get_node_api_v1_taxonomy_nodes__node_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Rename, reorder or translate a syllabus item
         * @description Send the ETag you last read in `If-Match`. The kind and parent never change.
         */
        patch: operations["update_node_api_v1_taxonomy_nodes__node_id__patch"];
        trace?: never;
    };
    "/api/v1/taxonomy/nodes/{node_id}/deprecate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Retire a syllabus item
         * @description It can no longer be chosen for new questions; questions that already use it keep it. Items under it are not changed.
         */
        post: operations["deprecate_node_api_v1_taxonomy_nodes__node_id__deprecate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/nodes/{node_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bring a retired syllabus item back */
        post: operations["restore_node_api_v1_taxonomy_nodes__node_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/concepts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Concepts, in name order
         * @description Filter by `subject_id` and `state` (use `state=ACTIVE` for a picker for a new question). `q` finds concepts whose name or an alias contains the text, in any case or spacing.
         */
        get: operations["list_concepts_api_v1_taxonomy_concepts_get"];
        put?: never;
        /**
         * Add a concept
         * @description Owner and admins. A concept belongs under a subject and never changes subject. Its name and aliases must differ from every other name and alias in the subject. Send an `Idempotency-Key` so a retry after a lost response returns the same concept.
         */
        post: operations["create_concept_api_v1_taxonomy_concepts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/concepts/{concept_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One concept
         * @description The ETag is its revision, for changes that need `If-Match`.
         */
        get: operations["get_concept_api_v1_taxonomy_concepts__concept_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Rename a concept, or change its other-language names or aliases
         * @description Send the ETag you last read in `If-Match`. The subject never changes.
         */
        patch: operations["update_concept_api_v1_taxonomy_concepts__concept_id__patch"];
        trace?: never;
    };
    "/api/v1/taxonomy/concepts/{concept_id}/deprecate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Retire a concept
         * @description It can no longer be chosen for new questions; questions that use it keep it.
         */
        post: operations["deprecate_concept_api_v1_taxonomy_concepts__concept_id__deprecate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/concepts/{concept_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bring a retired concept back */
        post: operations["restore_concept_api_v1_taxonomy_concepts__concept_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/import-template": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * A CSV file to start an import from
         * @description One row per syllabus item or concept. Open it in Excel or any spreadsheet, fill it in, and upload it (as CSV or saved as .xlsx). Parts of a path are separated by `>`; a name that contains `>` is written with a backslash before it (`v \> u`).
         */
        get: operations["import_template_api_v1_taxonomy_import_template_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/imports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Upload a syllabus file and see what it would do
         * @description Owner and admins. Send the file itself as the request body (`.xlsx` or UTF-8 `.csv`, up to 5 MB and 20,000 rows) and its name in `file_name`. **Nothing in the syllabus changes**: the result lists every row as new, changed, unchanged or an error, with the reason for each error. A file that cannot be read at all is refused (`IMPORT_INVALID`). Send an `Idempotency-Key` so a retry returns the same preview. Reading a file is heavy work, so a user may upload only a few files in a short time and the server reads only a few files at once: beyond that the answer is `429` (`RATE_LIMITED`) with a `Retry-After` header.
         */
        post: operations["create_import_api_v1_taxonomy_imports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/imports/{import_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One import preview: its totals */
        get: operations["read_import_api_v1_taxonomy_imports__import_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/imports/{import_id}/rows": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The rows of an import preview, in file order
         * @description Filter with `status=ERROR` to see only what needs fixing.
         */
        get: operations["read_import_rows_api_v1_taxonomy_imports__import_id__rows_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/taxonomy/imports/{import_id}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply an import preview to the syllabus
         * @description Owner and admins. Adds the new items and fills in the changed ones, **all or nothing**, exactly as the preview listed them. Nothing is removed, renamed, retired or restored. Applying a preview that is already applied changes nothing and returns it again. Refused if any row is an error, if there is nothing to do, or if it would add or change more than 5,000 rows at once (`IMPORT_INVALID`); and if the syllabus has changed since the preview was made (`IMPORT_STALE`): upload the file again.
         */
        post: operations["apply_import_api_v1_taxonomy_imports__import_id__apply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exams": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Exams, in name order
         * @description Retired exams are included unless you ask for `state=ACTIVE`, which is what a picker for a new question should do.
         */
        get: operations["list_exams_api_v1_exams_get"];
        put?: never;
        /**
         * Add an exam
         * @description Owner and admins. Send an `Idempotency-Key` so a retry after a lost response returns the same exam instead of failing.
         */
        post: operations["create_exam_api_v1_exams_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exams/{exam_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One exam
         * @description The ETag is its revision, for changes that need `If-Match`.
         */
        get: operations["get_exam_api_v1_exams__exam_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Rename an exam or change its short code
         * @description Send the ETag you last read in `If-Match`.
         */
        patch: operations["update_exam_api_v1_exams__exam_id__patch"];
        trace?: never;
    };
    "/api/v1/exams/{exam_id}/deprecate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Retire an exam
         * @description It can no longer be chosen for new questions; questions that use it keep it.
         */
        post: operations["deprecate_exam_api_v1_exams__exam_id__deprecate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exams/{exam_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bring a retired exam back */
        post: operations["restore_exam_api_v1_exams__exam_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sources, in name order
         * @description Filter by `kind`. Retired sources are included unless you ask for `state=ACTIVE`.
         */
        get: operations["list_sources_api_v1_sources_get"];
        put?: never;
        /**
         * Add a source
         * @description Owner and admins. Send an `Idempotency-Key` so a retry after a lost response returns the same source instead of failing.
         */
        post: operations["create_source_api_v1_sources_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/{source_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One source
         * @description The ETag is its revision, for changes that need `If-Match`.
         */
        get: operations["get_source_api_v1_sources__source_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Rename a source
         * @description Send the ETag you last read in `If-Match`. The kind never changes.
         */
        patch: operations["update_source_api_v1_sources__source_id__patch"];
        trace?: never;
    };
    "/api/v1/sources/{source_id}/deprecate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Retire a source
         * @description It can no longer be chosen for new questions; questions that use it keep it.
         */
        post: operations["deprecate_source_api_v1_sources__source_id__deprecate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/{source_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bring a retired source back */
        post: operations["restore_source_api_v1_sources__source_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Questions you may open, newest first
         * @description Your own drafts; admins and people with the edit-others grant see every draft in the coaching (`mine=true` narrows it to their own). Archived questions are left out unless you ask for `archived=true`, which lists only them. Each row carries the number of findings by level; open a question for the findings themselves.
         */
        get: operations["list_questions_api_v1_questions_get"];
        put?: never;
        /**
         * Start a question
         * @description Anyone in the coaching. A draft with gaps is saved; the findings in the answer say what is missing. Send an `Idempotency-Key` so a retry after a lost response returns the same question instead of making a second one.
         */
        post: operations["create_question_api_v1_questions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/by-code/{code}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One question, found by its code
         * @description Typed codes are forgiven: lower case, spaces and dashes are fine.
         */
        get: operations["get_question_by_code_api_v1_questions_by_code__code__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One question
         * @description The ETag is the working revision, for the changes that need `If-Match`.
         */
        get: operations["get_question_api_v1_questions__question_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/working-revision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Autosave: replace the working content
         * @description Send the whole content and the ETag you last read in `If-Match`. A save from a stale screen is refused (412) instead of overwriting newer work. Gaps and mistakes are saved and come back as findings. Not written to the audit log (it would bury it).
         */
        put: operations["save_working_revision_api_v1_questions__question_id__working_revision_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/checkpoints": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Save a checkpoint
         * @description Freezes the working revision for good (with a hash of its content) and starts a new working revision as a copy. The answer is that new working revision; its ETag is for the next save. `Location` is the frozen revision.
         */
        post: operations["save_checkpoint_api_v1_questions__question_id__checkpoints_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The saved revisions, newest first
         * @description The working revision on top, then the checkpoints. Contents are not included; open one revision for its content.
         */
        get: operations["list_revisions_api_v1_questions__question_id__revisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/revisions/{number}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One revision of the current version
         * @description Read-only. Findings are computed as of now, with today's rules.
         */
        get: operations["get_revision_api_v1_questions__question_id__revisions__number__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Archive a question
         * @description Hides it from the default list and stops edits; the code stays reserved and the question can still be read. Its author or an admin only. Doing it twice is harmless.
         */
        post: operations["archive_question_api_v1_questions__question_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Restore an archived question
         * @description Its author or an admin only. Doing it twice is harmless.
         */
        post: operations["restore_question_api_v1_questions__question_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountLinkOut */
        AccountLinkOut: {
            /**
             * Token
             * @description Shown only now. The web app turns it into `<app address>/activate#<token>` for an activation link, and `<app address>/activate#<token>.reset` for a password-reset link (the mark tells the page not to offer Google, which cannot use a reset link). Any earlier link of the same kind for this member stops working.
             */
            token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** ActIn */
        ActIn: {
            /**
             * Organization Id
             * Format: uuid
             */
            organization_id: string;
        };
        /** ActivationLink */
        ActivationLink: {
            /**
             * Token
             * @description Shown only now. The web app turns it into `<app address>/activate#<token>`.
             */
            token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** AuditActor */
        AuditActor: {
            /** User Id */
            user_id: string | null;
            /**
             * Display Name
             * @description Null when the person is not visible here, e.g. a platform admin.
             */
            display_name: string | null;
            /**
             * Is Platform Admin
             * @description The change was made with platform authority.
             */
            is_platform_admin: boolean;
        };
        /** AuditEventOut */
        AuditEventOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Action
             * @example USER_SIGNED_OUT
             */
            action: string;
            /** Entity Type */
            entity_type: string;
            /** Entity Id */
            entity_id: string | null;
            actor: components["schemas"]["AuditActor"];
            /** Before */
            before: {
                [key: string]: unknown;
            } | null;
            /** After */
            after: {
                [key: string]: unknown;
            } | null;
            /** Request Id */
            request_id: string | null;
        };
        /** AuditEventPage */
        AuditEventPage: {
            /** Data */
            data: components["schemas"]["AuditEventOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** AuthMethods */
        AuthMethods: {
            /**
             * Password
             * @description Sign-in with email and password is always available.
             */
            password: boolean;
            /**
             * Google
             * @description Google sign-in is set up on this server; show its button.
             */
            google: boolean;
        };
        /** BloomLevelOut */
        BloomLevelOut: {
            /**
             * Key
             * @example APPLY
             */
            key: string;
            /** Label */
            label: string;
        };
        /** ChangeRole */
        ChangeRole: {
            /**
             * Expected Role
             * @description The role the screen showed. If they have another role now, nothing changes.
             * @enum {string}
             */
            expected_role: "OWNER" | "ADMIN" | "FACULTY";
            /**
             * New Role
             * @description Faculty to admin promotes; admin to faculty demotes (and clears grants).
             * @enum {string}
             */
            new_role: "ADMIN" | "FACULTY";
        };
        /** ConceptOut */
        ConceptOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Subject Id
             * Format: uuid
             */
            subject_id: string;
            /** Name */
            name: string;
            /** Labels */
            labels: {
                [key: string]: string;
            };
            /**
             * Aliases
             * @description In alphabetical order.
             */
            aliases: string[];
            /**
             * State
             * @description DEPRECATED concepts cannot be chosen for new questions.
             * @enum {string}
             */
            state: "ACTIVE" | "DEPRECATED";
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ConceptPage */
        ConceptPage: {
            /** Data */
            data: components["schemas"]["ConceptOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** CreateConcept */
        CreateConcept: {
            /**
             * Subject Id
             * Format: uuid
             * @description The subject this concept belongs to; it never changes.
             */
            subject_id: string;
            /**
             * Name
             * @description The English name.
             * @example Newton's second law
             */
            name: string;
            /** Labels */
            labels?: {
                [key: string]: string;
            };
            /**
             * Aliases
             * @example [
             *       "Newton's 2nd law"
             *     ]
             */
            aliases?: string[];
        };
        /** CreateExam */
        CreateExam: {
            /**
             * Name
             * @example JEE Main
             */
            name: string;
            /**
             * Short Code
             * @example JEEM
             */
            short_code?: string | null;
        };
        /** CreateNode */
        CreateNode: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "CLASS" | "SUBJECT" | "CHAPTER" | "TOPIC" | "SUBTOPIC";
            /**
             * Parent Id
             * @description The item it sits under (a subject sits under a class). None for a class.
             */
            parent_id?: string | null;
            /**
             * Name
             * @description The English name.
             * @example Kinematics
             */
            name: string;
            /** Labels */
            labels?: {
                [key: string]: string;
            };
            /**
             * Sort Order
             * @description Smaller comes first.
             * @default 0
             */
            sort_order: number;
        };
        /** CreateOrganization */
        CreateOrganization: {
            /**
             * Display Name
             * @example Sharma Classes
             */
            display_name: string;
            /**
             * Timezone
             * @default Asia/Kolkata
             */
            timezone: string;
            owner: components["schemas"]["NewOwner"];
        };
        /** CreateQuestion */
        CreateQuestion: {
            /**
             * Content
             * @description The question's content (schema version 1). It may be incomplete: a draft with gaps is saved and the response lists what is missing.
             */
            content: {
                [key: string]: unknown;
            };
        };
        /** CreateSource */
        CreateSource: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "BOOK" | "MODULE" | "TEST_SERIES" | "PYQ_PAPER" | "OTHER";
            /**
             * Name
             * @example HC Verma, Concepts of Physics
             */
            name: string;
        };
        /** CreatedOrganization */
        CreatedOrganization: {
            organization: components["schemas"]["OrganizationOut"];
            owner: components["schemas"]["InvitedOwner"];
            /** @description A new activation link for the Owner. Null only when a retried request finds that the Owner has already activated their account. */
            activation: components["schemas"]["ActivationLink"] | null;
        };
        /** DifficultyLevelOut */
        DifficultyLevelOut: {
            /** Level */
            level: number;
            /** Meaning */
            meaning: string;
        };
        /** ErrorField */
        ErrorField: {
            /** Path */
            path: string;
            /** Code */
            code: string;
        };
        /** ErrorInfo */
        ErrorInfo: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Request Id */
            request_id: string | null;
            /** Fields */
            fields: components["schemas"]["ErrorField"][];
            /** Details */
            details: {
                [key: string]: unknown;
            };
        };
        /**
         * ErrorResponse
         * @description The one error envelope every API error uses (style guide §5); documented in OpenAPI.
         */
        ErrorResponse: {
            error: components["schemas"]["ErrorInfo"];
        };
        /** ExamOut */
        ExamOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Short Code */
            short_code: string | null;
            /**
             * State
             * @description DEPRECATED exams cannot be chosen for new questions.
             * @enum {string}
             */
            state: "ACTIVE" | "DEPRECATED";
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ExamPage */
        ExamPage: {
            /** Data */
            data: components["schemas"]["ExamOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** FindingCounts */
        FindingCounts: {
            /** Error */
            error: number;
            /** Incomplete */
            incomplete: number;
            /** Warning */
            warning: number;
        };
        /** FindingOut */
        FindingOut: {
            /**
             * Path
             * @description Which field, like `options[2].content[0].text`.
             * @example answer
             */
            path: string;
            /**
             * Code
             * @description Stable code to branch on, never the message.
             */
            code: string;
            level: components["schemas"]["Level"];
            /**
             * Message
             * @description Plain words for the author; the wording may change.
             */
            message: string;
        };
        /** GoogleActivationStartRequest */
        GoogleActivationStartRequest: {
            /**
             * Return Origin
             * @description The web address the person is on; must be one of ALLOWED_ORIGINS.
             * @example http://localhost:3000
             */
            return_origin: string;
            /**
             * Link Token
             * @description The part after # in the activation link.
             */
            link_token: string;
        };
        /** GoogleLinkStartRequest */
        GoogleLinkStartRequest: {
            /**
             * Return Origin
             * @description The web address the person is on; must be one of ALLOWED_ORIGINS.
             * @example http://localhost:3000
             */
            return_origin: string;
            /**
             * Password
             * @description The account's current password: a session alone never links Google.
             */
            password: string;
        };
        /** GoogleStartRequest */
        GoogleStartRequest: {
            /**
             * Purpose
             * @description What the person is doing at Google.
             * @constant
             */
            purpose: "SIGN_IN";
            /**
             * Return Origin
             * @description The web address the person is on; must be one of ALLOWED_ORIGINS.
             * @example http://localhost:3000
             */
            return_origin: string;
        };
        /** GoogleStartResponse */
        GoogleStartResponse: {
            /**
             * Authorization Url
             * @description Send the person's browser here.
             */
            authorization_url: string;
        };
        /** GoogleStatus */
        GoogleStatus: {
            /** Linked */
            linked: boolean;
            /**
             * Email
             * @description The Google account's email when it was linked.
             */
            email: string | null;
        };
        /**
         * Grant
         * @description Extra rights for faculty. Owner and admins hold all of them implicitly.
         * @enum {string}
         */
        Grant: "QC" | "APPROVE" | "PUBLISH" | "EDIT_OTHERS" | "MANAGE_AI_PROMPTS";
        /** ImportCounts */
        ImportCounts: {
            /**
             * New
             * @description Rows that would add something.
             */
            new: number;
            /**
             * Changed
             * @description Rows that would fill in or change something that exists.
             */
            changed: number;
            /**
             * Unchanged
             * @description Rows that match what is already there.
             */
            unchanged: number;
            /**
             * Error
             * @description Rows that cannot be imported. Any of these blocks applying.
             */
            error: number;
        };
        /** ImportOut */
        ImportOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** File Name */
            file_name: string;
            /**
             * State
             * @enum {string}
             */
            state: "PREVIEWED" | "APPLIED";
            counts: components["schemas"]["ImportCounts"];
            /**
             * Can Apply
             * @description True when no row is an error and something would be added or changed.
             */
            can_apply: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Applied At */
            applied_at: string | null;
        };
        /** ImportRowOut */
        ImportRowOut: {
            /**
             * Number
             * @description The row's number in the file (the header is row 1).
             */
            number: number;
            /** Kind */
            kind: string;
            /** Path */
            path: string;
            /**
             * Status
             * @enum {string}
             */
            status: "NEW" | "CHANGED" | "UNCHANGED" | "ERROR";
            /**
             * Message
             * @description For an error: why, in plain words.
             */
            message: string | null;
            /** Sort Order */
            sort_order: number | null;
            /** Labels */
            labels: {
                [key: string]: string;
            };
            /** Aliases */
            aliases: string[];
        };
        /** ImportRowPage */
        ImportRowPage: {
            /** Data */
            data: components["schemas"]["ImportRowOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** InviteMember */
        InviteMember: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Display Name */
            display_name: string;
            /**
             * Role
             * @description The Owner is created with the coaching and changes only by a transfer.
             * @enum {string}
             */
            role: "ADMIN" | "FACULTY";
        };
        /** InvitedMember */
        InvitedMember: {
            member: components["schemas"]["MemberOut"];
            /** @description The invitee's activation link. Null only when a retried request finds that they have already activated their account. */
            activation: components["schemas"]["ActivationLink"] | null;
        };
        /** InvitedOwner */
        InvitedOwner: {
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /**
             * Membership Id
             * Format: uuid
             */
            membership_id: string;
            /** Display Name */
            display_name: string;
            /** Email */
            email: string;
        };
        /** LanguageOut */
        LanguageOut: {
            /**
             * Tag
             * @example hi
             */
            tag: string;
            /** English Name */
            english_name: string;
            /** Native Name */
            native_name: string;
        };
        /**
         * Level
         * @enum {string}
         */
        Level: "error" | "incomplete" | "warning";
        /** LiveStatus */
        LiveStatus: {
            /**
             * Status
             * @constant
             */
            status: "ok";
        };
        /** LoginMethods */
        LoginMethods: {
            /**
             * Password
             * @description The account has a password.
             */
            password: boolean;
            google: components["schemas"]["GoogleStatus"];
        };
        /** LoginRequest */
        LoginRequest: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
        };
        /** LoginResponse */
        LoginResponse: {
            user: components["schemas"]["Me"];
            /**
             * Csrf Token
             * @description Send back in the X-CSRF-Token header on changes.
             */
            csrf_token: string;
        };
        /** Me */
        Me: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
            /** Is Platform Admin */
            is_platform_admin: boolean;
            organization: components["schemas"]["MyOrganization"] | null;
            /** Acting Organization Id */
            acting_organization_id: string | null;
            /**
             * Acting Organization Name
             * @description Name of the coaching a platform admin is acting in.
             */
            acting_organization_name?: string | null;
        };
        /** MemberOut */
        MemberOut: {
            /**
             * Membership Id
             * Format: uuid
             */
            membership_id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Display Name */
            display_name: string;
            /**
             * Email
             * @description Sign-in email; null only for an account without one
             */
            email: string | null;
            /**
             * Role
             * @description OWNER, ADMIN or FACULTY
             */
            role: string;
            /**
             * Status
             * @description Membership: ACTIVE or REMOVED
             */
            status: string;
            /**
             * Account Status
             * @description INVITED (not activated yet), ACTIVE or DISABLED
             */
            account_status: string;
            /**
             * Grants
             * @description Faculty grants (Owner and admins hold all implicitly)
             */
            grants: string[];
            /** Revision */
            revision: number;
            /**
             * Joined At
             * Format: date-time
             */
            joined_at: string;
            /**
             * Actions
             * @description What you may do to this member now: NEW_ACTIVATION_LINK, NEW_RESET_LINK, SET_GRANTS, CHANGE_ROLE, REMOVE, TRANSFER_OWNERSHIP. The web app shows only these buttons; the API checks again on every request.
             */
            actions: string[];
        };
        /** MemberPage */
        MemberPage: {
            /** Data */
            data: components["schemas"]["MemberOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** MyOrganization */
        MyOrganization: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
            /** Role */
            role: string;
            /**
             * Grants
             * @description Grants in effect (Owner and admins hold all of them), sorted by name.
             */
            grants: string[];
        };
        /** NewOwner */
        NewOwner: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Display Name */
            display_name: string;
        };
        /** NodeOut */
        NodeOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "CLASS" | "SUBJECT" | "CHAPTER" | "TOPIC" | "SUBTOPIC";
            /** Parent Id */
            parent_id: string | null;
            /** Name */
            name: string;
            /** Labels */
            labels: {
                [key: string]: string;
            };
            /**
             * State
             * @description DEPRECATED items cannot be chosen for new questions.
             * @enum {string}
             */
            state: "ACTIVE" | "DEPRECATED";
            /** Sort Order */
            sort_order: number;
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** NodePage */
        NodePage: {
            /** Data */
            data: components["schemas"]["NodeOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** OrganizationOut */
        OrganizationOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
            /**
             * Status
             * @description ACTIVE or SUSPENDED
             */
            status: string;
            /** Timezone */
            timezone: string;
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** OrganizationPage */
        OrganizationPage: {
            /** Data */
            data: components["schemas"]["OrganizationOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** OwnershipTransferred */
        OwnershipTransferred: {
            /** @description Now an admin. */
            previous_owner: components["schemas"]["MemberOut"];
            new_owner: components["schemas"]["MemberOut"];
        };
        /** PageInfo */
        PageInfo: {
            /**
             * Next Cursor
             * @description Pass as `cursor` to get the next page.
             */
            next_cursor: string | null;
            /** Has More */
            has_more: boolean;
        };
        /** QuestionOut */
        QuestionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Code
             * @description The permanent 8-character code, never reused.
             */
            code: string;
            /** Version Number */
            version_number: number;
            /**
             * Revision
             * @description Also the ETag of the working revision.
             */
            revision: number;
            /** Archived */
            archived: boolean;
            /**
             * Created By
             * Format: uuid
             */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Content */
            content: {
                [key: string]: unknown;
            };
            /**
             * Findings
             * @description Computed from the content on every read, never stored.
             */
            findings: components["schemas"]["FindingOut"][];
        };
        /** QuestionPage */
        QuestionPage: {
            /** Data */
            data: components["schemas"]["QuestionSummary"][];
            page: components["schemas"]["PageInfo"];
        };
        /** QuestionSummary */
        QuestionSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Code */
            code: string;
            /**
             * Question Type
             * @description From the content; null while not chosen.
             */
            question_type: string | null;
            /** Archived */
            archived: boolean;
            /**
             * Created By
             * Format: uuid
             */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            finding_counts: components["schemas"]["FindingCounts"];
        };
        /** ReadyStatus */
        ReadyStatus: {
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "unavailable";
            /**
             * Database
             * @enum {string}
             */
            database: "ok" | "unavailable";
            /**
             * Migrations
             * @enum {string}
             */
            migrations: "ok" | "pending" | "unknown";
        };
        /** RedeemLinkRequest */
        RedeemLinkRequest: {
            /**
             * Token
             * @description The part after # in the link.
             */
            token: string;
            /**
             * Password
             * @description The new password (at least 12 characters).
             */
            password: string;
        };
        /** RemoveMember */
        RemoveMember: {
            /**
             * Expected Role
             * @description The role the screen showed. If they have another role now, nothing changes.
             * @enum {string}
             */
            expected_role: "OWNER" | "ADMIN" | "FACULTY";
        };
        /** RevisionList */
        RevisionList: {
            /** Data */
            data: components["schemas"]["RevisionSummary"][];
        };
        /** RevisionOut */
        RevisionOut: {
            /**
             * Number
             * @description Counts up within the version.
             */
            number: number;
            /**
             * Working
             * @description The one being edited; the others are frozen checkpoints.
             */
            working: boolean;
            /** Version Number */
            version_number: number;
            /**
             * Author Id
             * Format: uuid
             * @description Who saved it last.
             */
            author_id: string;
            /**
             * Content Hash
             * @description SHA-256 of the content; set when frozen.
             */
            content_hash: string | null;
            /** Frozen At */
            frozen_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Content */
            content: {
                [key: string]: unknown;
            };
            /**
             * Findings
             * @description Computed as of now, with today's rules.
             */
            findings: components["schemas"]["FindingOut"][];
        };
        /** RevisionSummary */
        RevisionSummary: {
            /**
             * Number
             * @description Counts up within the version.
             */
            number: number;
            /**
             * Working
             * @description The one being edited; the others are frozen checkpoints.
             */
            working: boolean;
            /** Version Number */
            version_number: number;
            /**
             * Author Id
             * Format: uuid
             * @description Who saved it last.
             */
            author_id: string;
            /**
             * Content Hash
             * @description SHA-256 of the content; set when frozen.
             */
            content_hash: string | null;
            /** Frozen At */
            frozen_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** SaveQuestion */
        SaveQuestion: {
            /**
             * Content
             * @description The whole content, replacing the working revision's. Gaps are fine.
             */
            content: {
                [key: string]: unknown;
            };
        };
        /** SetGrants */
        SetGrants: {
            /**
             * Grants
             * @description The complete new set (an empty list removes all); repeats count once.
             * @example [
             *       "QC",
             *       "APPROVE"
             *     ]
             */
            grants: components["schemas"]["Grant"][];
        };
        /** SourceOut */
        SourceOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "BOOK" | "MODULE" | "TEST_SERIES" | "PYQ_PAPER" | "OTHER";
            /** Name */
            name: string;
            /**
             * State
             * @description DEPRECATED sources cannot be chosen for new questions.
             * @enum {string}
             */
            state: "ACTIVE" | "DEPRECATED";
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** SourcePage */
        SourcePage: {
            /** Data */
            data: components["schemas"]["SourceOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /** TransferOwnership */
        TransferOwnership: {
            /**
             * Expected Owner Membership Id
             * Format: uuid
             * @description The Owner the screen showed. If ownership has moved since, nothing changes.
             */
            expected_owner_membership_id: string;
            /**
             * New Owner Membership Id
             * Format: uuid
             * @description An active admin of this coaching, who becomes the Owner.
             */
            new_owner_membership_id: string;
        };
        /** UpdateConcept */
        UpdateConcept: {
            /** Name */
            name?: string | null;
            /**
             * Labels
             * @description Replaces all the other-language names when sent.
             */
            labels?: {
                [key: string]: string;
            } | null;
            /**
             * Aliases
             * @description Replaces all the aliases when sent.
             */
            aliases?: string[] | null;
        };
        /** UpdateExam */
        UpdateExam: {
            /** Name */
            name?: string | null;
            /**
             * Short Code
             * @description Send null to remove the short code; leave it out to keep it.
             */
            short_code?: string | null;
        };
        /** UpdateNode */
        UpdateNode: {
            /** Name */
            name?: string | null;
            /**
             * Labels
             * @description Replaces all the other-language names when sent.
             */
            labels?: {
                [key: string]: string;
            } | null;
            /** Sort Order */
            sort_order?: number | null;
        };
        /**
         * UpdateOrganization
         * @description Only the fields sent are changed.
         */
        UpdateOrganization: {
            /** Display Name */
            display_name?: string | null;
            /** Timezone */
            timezone?: string | null;
        };
        /** UpdateSource */
        UpdateSource: {
            /**
             * Name
             * @description The kind never changes.
             */
            name?: string | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    live_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LiveStatus"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    ready_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyStatus"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not ready */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyStatus"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Email or password is incorrect (one message for all cases) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many attempts; see the Retry-After header */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    redeem_link_api_v1_auth_links_redeem_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RedeemLinkRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The link is unknown, used, replaced, expired, or its membership or coaching is no longer active (`LINK_INVALID`, one message for all cases) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many attempts; see the Retry-After header */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website), `CSRF_TOKEN_INVALID` (missing or wrong X-CSRF-Token) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    me_api_v1_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    auth_methods_api_v1_auth_methods_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthMethods"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    start_google_api_v1_auth_google_start_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoogleStartRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoogleStartResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Google sign-in is not set up on this server (`GOOGLE_DISABLED`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `return_origin` is not an allowed web address (`RETURN_ORIGIN_NOT_ALLOWED`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many attempts; see the Retry-After header */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    start_google_activation_api_v1_auth_google_start_activation_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoogleActivationStartRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoogleStartResponse"];
                };
            };
            /** @description The activation link is unknown, used, replaced, expired, or its membership or coaching is no longer active (`LINK_INVALID`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Google sign-in is not set up on this server (`GOOGLE_DISABLED`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `return_origin` is not an allowed web address (`RETURN_ORIGIN_NOT_ALLOWED`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many attempts; see the Retry-After header */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    start_google_link_api_v1_auth_google_start_link_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoogleLinkStartRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoogleStartResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The password is incorrect (`PASSWORD_INCORRECT`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Google sign-in is not set up on this server (`GOOGLE_DISABLED`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A Google account is already linked (`ALREADY_LINKED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `return_origin` is not an allowed web address (`RETURN_ORIGIN_NOT_ALLOWED`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many attempts; see the Retry-After header */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    unlink_google_api_v1_auth_google_unlink_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website), `CSRF_TOKEN_INVALID` (missing or wrong X-CSRF-Token) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No Google account is linked (`GOOGLE_NOT_LINKED`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Google is the only way to sign in; a password must remain (`NO_OTHER_LOGIN_METHOD`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    my_login_methods_api_v1_me_login_methods_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginMethods"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    google_callback_api_v1_auth_google_callback_get: {
        parameters: {
            query?: {
                code?: string | null;
                state?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Redirect to the home page, to `/profile?google=linked`, or to the failure address */
            303: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_audit_events_api_v1_audit_events_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                entity_type?: string | null;
                entity_id?: string | null;
                actor_user_id?: string | null;
                /** @description Events at or after this time (with time zone). */
                since?: string | null;
                /** @description Events before this time (with time zone). */
                until?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditEventPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only the Owner and admins may read it (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_organizations_api_v1_platform_organizations_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_organization_api_v1_platform_organizations_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateOrganization"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreatedOrganization"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The Owner's email already has an account (`EMAIL_TAKEN`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_organization_api_v1_platform_organizations__organization_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                organization_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_organization_api_v1_platform_organizations__organization_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                organization_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateOrganization"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    suspend_organization_api_v1_platform_organizations__organization_id__suspend_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                organization_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reactivate_organization_api_v1_platform_organizations__organization_id__reactivate_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                organization_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    start_acting_api_v1_platform_acting_organization_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    stop_acting_api_v1_platform_acting_organization_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only platform admins may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_members_api_v1_members_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_member_api_v1_members__membership_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    invite_member_api_v1_members_invitations_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InviteMember"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitedMember"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The email already has an account, in any coaching (`EMAIL_TAKEN`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    new_activation_link_api_v1_members__membership_id__activation_link_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountLinkOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Wrong kind of link for this account (`ALREADY_ACTIVATED` or `NOT_ACTIVATED`), the account is disabled (`ACCOUNT_DISABLED`), or they are no longer a member (`MEMBER_REMOVED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    new_reset_link_api_v1_members__membership_id__reset_link_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountLinkOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Wrong kind of link for this account (`ALREADY_ACTIVATED` or `NOT_ACTIVATED`), the account is disabled (`ACCOUNT_DISABLED`), or they are no longer a member (`MEMBER_REMOVED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    set_grants_api_v1_members__membership_id__grants_put: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetGrants"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The member is not faculty (`NOT_FACULTY`), or no longer a member (`MEMBER_REMOVED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    change_role_api_v1_members__membership_id__change_role_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangeRole"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The person was already removed (`MEMBER_REMOVED`), their role is not the one you named (`ROLE_CHANGED`), or they are the Owner (`LAST_OWNER`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    remove_member_api_v1_members__membership_id__remove_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                membership_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RemoveMember"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The person was already removed (`MEMBER_REMOVED`), their role is not the one you named (`ROLE_CHANGED`), or they are the Owner (`LAST_OWNER`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    transfer_ownership_api_v1_organization_transfer_ownership_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TransferOwnership"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OwnershipTransferred"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Only the Owner may do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such member in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The Owner is someone else now (`OWNER_CHANGED`), or the new Owner is not an active admin (`INVALID_NEW_OWNER`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since your read (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The If-Match header is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_languages_api_v1_languages_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LanguageOut"][];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_bloom_levels_api_v1_catalogues_bloom_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BloomLevelOut"][];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    difficulty_guide_api_v1_catalogues_difficulty_guide_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DifficultyLevelOut"][];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_nodes_api_v1_taxonomy_nodes_get: {
        parameters: {
            query?: {
                kind?: ("CLASS" | "SUBJECT" | "CHAPTER" | "TOPIC" | "SUBTOPIC") | null;
                parent_id?: string | null;
                state?: ("ACTIVE" | "DEPRECATED") | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodePage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_node_api_v1_taxonomy_nodes_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateNode"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A sibling has this name (`DUPLICATE_NAME`), the parent is retired (`PARENT_DEPRECATED`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Wrong kind of parent (`HIERARCHY_INVALID`) or a name that is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_node_api_v1_taxonomy_nodes__node_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_node_api_v1_taxonomy_nodes__node_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateNode"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A sibling has this name (`DUPLICATE_NAME`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The name is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    deprecate_node_api_v1_taxonomy_nodes__node_id__deprecate_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_node_api_v1_taxonomy_nodes__node_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Its parent is retired; restore that first (`PARENT_DEPRECATED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_concepts_api_v1_taxonomy_concepts_get: {
        parameters: {
            query?: {
                subject_id?: string | null;
                state?: ("ACTIVE" | "DEPRECATED") | null;
                q?: string | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptPage"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A name or alias is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_concept_api_v1_taxonomy_concepts_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateConcept"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such subject in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A name or alias is taken in this subject (`DUPLICATE_NAME`), the subject is retired (`PARENT_DEPRECATED`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The parent is not a subject (`HIERARCHY_INVALID`), or a name or alias is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_concept_api_v1_taxonomy_concepts__concept_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                concept_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such concept (or subject) in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_concept_api_v1_taxonomy_concepts__concept_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                concept_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateConcept"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such concept (or subject) in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A name or alias is taken in this subject (`DUPLICATE_NAME`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description A name or alias is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    deprecate_concept_api_v1_taxonomy_concepts__concept_id__deprecate_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                concept_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such concept (or subject) in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_concept_api_v1_taxonomy_concepts__concept_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                concept_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConceptOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such concept (or subject) in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Its subject is retired; restore that first (`PARENT_DEPRECATED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    import_template_api_v1_taxonomy_import_template_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                    "text/csv": unknown;
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_import_api_v1_taxonomy_imports_post: {
        parameters: {
            query: {
                file_name: string;
            };
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/octet-stream": string;
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The Idempotency-Key was used for a different file (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The file cannot be read (`IMPORT_INVALID`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many uploads in a short time, or the server is busy reading other files; see the Retry-After header (`RATE_LIMITED`) */
            429: {
                headers: {
                    /** @description Seconds to wait before trying again */
                    "Retry-After"?: number;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    read_import_api_v1_taxonomy_imports__import_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such import in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The preview was kept too long and its rows are gone; upload the file again (`IMPORT_EXPIRED`) */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    read_import_rows_api_v1_taxonomy_imports__import_id__rows_get: {
        parameters: {
            query?: {
                status?: ("NEW" | "CHANGED" | "UNCHANGED" | "ERROR") | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportRowPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such import in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The preview was kept too long and its rows are gone; upload the file again (`IMPORT_EXPIRED`) */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    apply_import_api_v1_taxonomy_imports__import_id__apply_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such import in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The syllabus changed after the preview (`IMPORT_STALE`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The preview was kept too long and its rows are gone; upload the file again (`IMPORT_EXPIRED`) */
            410: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not applicable: error rows, nothing to do, too many (`IMPORT_INVALID`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_exams_api_v1_exams_get: {
        parameters: {
            query?: {
                state?: ("ACTIVE" | "DEPRECATED") | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_exam_api_v1_exams_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateExam"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Another item has this name (`DUPLICATE_NAME`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The name is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_exam_api_v1_exams__exam_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                exam_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_exam_api_v1_exams__exam_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                exam_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateExam"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Another item has this name (`DUPLICATE_NAME`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The name is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    deprecate_exam_api_v1_exams__exam_id__deprecate_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                exam_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_exam_api_v1_exams__exam_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                exam_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExamOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_sources_api_v1_sources_get: {
        parameters: {
            query?: {
                kind?: ("BOOK" | "MODULE" | "TEST_SERIES" | "PYQ_PAPER" | "OTHER") | null;
                state?: ("ACTIVE" | "DEPRECATED") | null;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourcePage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_source_api_v1_sources_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateSource"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Another item has this name (`DUPLICATE_NAME`), or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The name is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_source_api_v1_sources__source_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_source_api_v1_sources__source_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateSource"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Another item has this name (`DUPLICATE_NAME`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The name is too long once normalised for comparing (`NAME_TOO_LONG`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    deprecate_source_api_v1_sources__source_id__deprecate_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_source_api_v1_sources__source_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such item in your coaching (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed by someone else since you read it (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_questions_api_v1_questions_get: {
        parameters: {
            query?: {
                mine?: boolean;
                archived?: boolean;
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionPage"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_question_api_v1_questions_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Any unique string (e.g. a UUID). Retrying with the same key never creates twice. */
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateQuestion"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The Idempotency-Key was used for a different request */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too large (`CONTENT_TOO_LARGE`) or not plain data (`CONTENT_NOT_JSON`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_question_by_code_api_v1_questions_by_code__code__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not a code (`INVALID_CODE`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_question_api_v1_questions__question_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    save_working_revision_api_v1_questions__question_id__working_revision_put: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SaveQuestion"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The question is archived (`QUESTION_ARCHIVED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed since you read it; reload (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    save_checkpoint_api_v1_questions__question_id__checkpoints_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The question is archived (`QUESTION_ARCHIVED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed since you read it; reload (`REVISION_STALE`) */
            412: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description `If-Match` is missing (`IF_MATCH_REQUIRED`) */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_revisions_api_v1_questions__question_id__revisions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionList"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_revision_api_v1_questions__question_id__revisions__number__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
                number: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    archive_question_api_v1_questions__question_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_question_api_v1_questions__question_id__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
            /** @description The request is not valid (`MALFORMED_REQUEST`) */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not signed in (`UNAUTHENTICATED`) */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected server error (`INTERNAL_ERROR`); quote the request_id */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
