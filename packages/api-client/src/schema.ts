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
    "/api/v1/assets/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Upload a picture
         * @description Any member of the coaching. Send the picture itself as the request body: PNG, JPEG or WebP, up to 10 MB and 40 megapixels. The server decides what the file is from its bytes (not its name or `Content-Type`), decodes it and stores a **re-encoded** copy, so location and camera data and anything else hidden in the file are gone; the width and height in the answer are those of the stored copy. SVG, GIF, HEIC, animated and unreadable files are refused (`IMAGE_INVALID`). Cropping is done in the browser first. Reading a picture is heavy work, so a user may upload only a limited number in a short time and the server decodes only a few at once: beyond that the answer is `429` (`RATE_LIMITED`) with a `Retry-After` header.
         */
        post: operations["upload_image_api_v1_assets_images_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** What is known about one picture */
        get: operations["read_asset_api_v1_assets__asset_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/{asset_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The picture itself
         * @description Any member of the coaching; another coaching's picture answers 404. The `Content-Type` comes from our own record. The browser may keep the picture but must ask again each time (`Cache-Control: private, no-cache`), so a person who signs in on the same browser is checked afresh; if it has not changed (`If-None-Match`) the answer is `304`.
         */
        get: operations["read_content_api_v1_assets__asset_id__content_get"];
        put?: never;
        post?: never;
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
    "/api/v1/questions/{question_id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send the question for review
         * @description Freezes the working revision as the one under review and makes the question readable by every member of the coaching. Send the working revision's ETag (`rev-N`) in `If-Match`. Things still to do are allowed; mistakes (`error` findings) are refused with `QUESTION_HAS_ERRORS`. The editor is read-only until the question is withdrawn.
         */
        post: operations["submit_question_api_v1_questions__question_id__submit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/withdraw": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Take the question back from review to edit it
         * @description From in review, passed QC or approved, back to draft. The decisions so far stay in the history. Send the workflow ETag (`flow-N`, from the question) in `If-Match`.
         */
        post: operations["withdraw_question_api_v1_questions__question_id__withdraw_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/return": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send the question back to its author
         * @description From in review (QC grant), passed QC (approve grant) or approved (publish grant). Needs one or more reasons from the list and a note of at least 10 characters (`RETURN_REASON_REQUIRED`). The question becomes the author's draft again. Send the workflow ETag (`flow-N`) in `If-Match`.
         */
        post: operations["return_question_api_v1_questions__question_id__return_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/pass-qc": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Pass quality control
         * @description Quality control accepts the frozen revision. Allowed only when it has no `error` and no `incomplete` finding against the coaching's current lists and limits (`PUBLICATION_CHECKLIST_FAILED`). Send the workflow ETag (`flow-N`) in `If-Match`.
         */
        post: operations["pass_qc_question_api_v1_questions__question_id__pass_qc_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Approve the question
         * @description Approves the revision that passed QC. The publication checklist is checked again, because the lists or limits may have changed since QC (`PUBLICATION_CHECKLIST_FAILED`). Send the workflow ETag (`flow-N`) in `If-Match`.
         */
        post: operations["approve_question_api_v1_questions__question_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Publish the approved question
         * @description Publishes the approved revision; from then on the version never changes. The publication checklist is checked again, because the lists or limits may have changed since QC (`PUBLICATION_CHECKLIST_FAILED`). The names of its labels are kept with the publication. Send the workflow ETag (`flow-N`) in `If-Match`.
         */
        post: operations["publish_question_api_v1_questions__question_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/start-correction": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start a correction of a published question
         * @description Starts the next version of the same question (same code) as a draft copy of the published text. The published version stays what everyone reads until the new one is published. Only one correction can be open (`CORRECTION_ALREADY_OPEN`, with `details.version_id`). Send the published version's workflow ETag (`flow-N`) in `If-Match`.
         */
        post: operations["start_correction_question_api_v1_questions__question_id__start_correction_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Who did what to a question, oldest first (E-09)
         * @description The start of the question, each saved checkpoint, every review step (a return with its reasons and note), the start of a correction, and archive and restore. Only the versions you may read are included: the steps of a correction that is still a private draft are not listed to someone who may read only the published version.
         */
        get: operations["get_history_api_v1_questions__question_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/diff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * What changed between two saved texts of a question (E-08)
         * @description `from` and `to` are revision ids (from the history or the revision list); both must belong to this question, and each is checked on its own against what you may read. Changed prose comes with word-level segments; an equation or picture counts as one item.
         */
        get: operations["get_diff_api_v1_questions__question_id__diff_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/duplicates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Possible duplicates of a question (D-16)
         * @description Questions of this coaching with the same content (`EXACT`) or very similar text (`NEAR`), at most 20 of each, never archived ones, never another coaching's, and only ones you may open, with the newest decision about each. A person decides whether they are duplicates; nothing is merged or changed.
         */
        get: operations["get_duplicates_api_v1_questions__question_id__duplicates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/questions/{question_id}/duplicates/decisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Record whether a question is a duplicate of another (D-16)
         * @description For the text as it is now: an edit that changes the question needs a new decision, and a newer decision replaces an older one (both are kept). The author, admins, edit-others holders and quality control may decide. An exact match with no `NOT_DUPLICATE` decision, or a `DUPLICATE_OF`, blocks Pass QC (`QC_BLOCKED_DUPLICATE`). Nothing is merged or deleted.
         */
        post: operations["decide_duplicate_api_v1_questions__question_id__duplicates_decisions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Passages you may open, newest first
         * @description Your own drafts; admins and people with the edit-others grant see every passage in the coaching (`mine=true` narrows it to their own).
         */
        get: operations["list_passages_api_v1_passages_get"];
        put?: never;
        /**
         * Start a passage
         * @description Anyone in the coaching. A passage is shared text that several questions sit under; it has no public code. Leave `content` out to start an empty one. Send an `Idempotency-Key` so a retry after a lost response returns the same passage.
         */
        post: operations["create_passage_api_v1_passages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages/{passage_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One passage
         * @description The ETag is the working revision, for the changes that need `If-Match`.
         */
        get: operations["get_passage_api_v1_passages__passage_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages/{passage_id}/working-revision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Autosave: replace the working content
         * @description Send the whole content and the ETag you last read in `If-Match`. A save from a stale screen is refused (412) instead of overwriting newer work. Gaps and mistakes are saved and come back as findings.
         */
        put: operations["save_working_revision_api_v1_passages__passage_id__working_revision_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages/{passage_id}/checkpoints": {
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
         * @description Freezes the working revision for good (with a hash of its content) and starts a new working revision as a copy. The answer is that new working revision, whose `latest_checkpoint` is the revision just frozen: the one a child question pins.
         */
        post: operations["save_checkpoint_api_v1_passages__passage_id__checkpoints_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages/{passage_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The saved revisions, newest first
         * @description The working revision first, then the checkpoints.
         */
        get: operations["list_revisions_api_v1_passages__passage_id__revisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passages/{passage_id}/children": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The questions under a passage
         * @description Each question that pins a checkpoint of this passage, in the order of its number, with the checkpoint it was written with and whether the passage has a newer one (`is_current` false). Questions are drafts of their authors, so ones you may not open are not listed; `hidden_count` says how many. A very long list is cut after 500 children and `truncated` says so.
         */
        get: operations["list_children_api_v1_passages__passage_id__children_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/passage-revisions/{revision_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One checkpoint of a passage, by its id
         * @description What a child question pins in `context.passage_revision_id`. Any member of the coaching may read it, because the questions under it show it; a draft (working) revision is not served here and answers 404.
         */
        get: operations["get_checkpoint_api_v1_passage_revisions__revision_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/settings/answer-rules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The answer limits of the coaching
         * @description Owner and admins. The built-in values, the widest range each setting may take, and what this coaching changed (for itself and for particular exams). The ETag is for the save. A changed limit never rewrites a saved revision; it only changes what the findings say.
         */
        get: operations["get_answer_rules_api_v1_settings_answer_rules_get"];
        /**
         * Change the answer limits of the coaching
         * @description Owner and admins. Send everything that differs from the built-in values, with the ETag you last read in `If-Match` (`"rev-0"` before the first save); a save from a stale screen is refused (412). A minimum above its maximum, a value outside its bounds, an unknown setting or an exam that is not this coaching's is refused with every problem listed (`ANSWER_RULES_INVALID`). The change is written to the audit log.
         */
        put: operations["save_answer_rules_api_v1_settings_answer_rules_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Your notifications, newest first (I-01)
         * @description The screen reads this on load and about once a minute. A person sees and marks only their own notifications; another person's is not found.
         */
        get: operations["list_notifications_api_v1_notifications_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notifications/unread-count": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * How many notifications you have not read (the bell)
         * @description A person sees and marks only their own notifications; another person's is not found.
         */
        get: operations["unread_count_api_v1_notifications_unread_count_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notifications/read-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Mark all your notifications as read
         * @description Safe to repeat: a second call marks nothing and answers `updated: 0`.
         */
        post: operations["read_all_api_v1_notifications_read_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notifications/{notification_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Mark one notification as read
         * @description Safe to repeat: the first read time stays. A person sees and marks only their own notifications; another person's is not found.
         */
        post: operations["read_one_api_v1_notifications__notification_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bank/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The bank: questions with filters and a total (F-01, F-02)
         * @description The most recently changed first. Each question shows the version everyone reads: the published one if there is one, else the newest. Filters combine with AND; give a filter several times to match any of its values. `total` counts every match, not only this page. A draft, or a returned question, is listed only to its author, admins and holders of the edit-others grant; to everyone else it does not exist. `archived=true` lists the archive.
         */
        get: operations["list_bank_api_v1_bank_questions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bank/questions/by-code/{code}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * One question of the bank, found by its code (F-02)
         * @description Typed codes are forgiven: lower case, spaces and dashes are fine, and `O`, `I` and `L` read as `0`, `1` and `1`. Another coaching's code, a code that does not exist and a private draft that is not yours all answer 404.
         */
        get: operations["get_by_code_api_v1_bank_questions_by_code__code__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/review/queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The review queue, oldest first (E-05)
         * @description What waits for QC, approval or publication, the longest-waiting first. For people who hold at least one of the QC, approve and publish grants, and for admins. A question that is still a draft, or that came back to someone else, is never shown. `state` picks one view; `CHANGES_REQUESTED` is the questions you sent in that came back, and it is yours alone. Left out, you get everything that waits. Each row is the newest version of its question; a correction shows as version 2 or more. The labels and language are those of the text the reviewers act on. `author_id` is whoever sent that version in.
         */
        get: operations["get_queue_api_v1_review_queue_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/review/queue/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * How many wait at each step
         * @description The size of each tab of the queue, not narrowed by any filter. For people who hold at least one of the QC, approve and publish grants, and for admins. A question that is still a draft, or that came back to someone else, is never shown.
         */
        get: operations["get_counts_api_v1_review_queue_counts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/keys": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Which provider keys the coaching has stored (H-02)
         * @description Owner and admins. One entry per provider: whether a key is stored and its last four characters. **A key is never returned.** `encryption_ready` is false when the server has no master encryption key, and then no key can be stored.
         */
        get: operations["list_keys_api_v1_ai_keys_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/keys/{provider}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Store or replace the coaching's key for a provider (H-02)
         * @description Owner and admins. The key is sealed on the server with the master encryption key and cannot be read back: write-only. Replacing a key replaces it for every run from now on. The change is written to the audit log with the last four characters only.
         */
        put: operations["set_key_api_v1_ai_keys__provider__put"];
        post?: never;
        /**
         * Remove the coaching's key for a provider
         * @description Owner and admins. AI runs that need this provider stop working until a key is stored again. Written to the audit log.
         */
        delete: operations["delete_key_api_v1_ai_keys__provider__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * The coaching's AI models, as the providers list them (H-17)
         * @description Owner and admins. Every model the providers' lists have shown for this coaching, with the facts a run relies on (**effective**: the admin's entry where there is one, else the provider's, else unknown) and whether it is enabled. `providers` says when each list was last fetched and how the last try ended. A model the provider no longer lists stays here as `available: false`.
         */
        get: operations["list_models_api_v1_ai_models_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/models/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Fetch a provider's model list again (H-17)
         * @description Owner and admins. Starts a background job that asks the provider for its list with the coaching's stored key and updates the rows. Pressing it twice in a minute starts one job. Read `providers` in the model list to see when it finished and whether it worked; a failure is not retried by itself.
         */
        post: operations["refresh_models_api_v1_ai_models_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/models/{model_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Enable or disable a model, or set the admin's own facts about it (H-03, H-17)
         * @description Owner and admins. `enabled` offers the model to faculty (a model the provider no longer lists cannot be enabled: `AI_MODEL_UNAVAILABLE`). `overlay` holds the admin's own capability and price entries, which win over the provider's; send only what changes, and `null` to remove one. Send the ETag you last read in `If-Match`. Written to the audit log.
         */
        patch: operations["update_model_api_v1_ai_models__model_id__patch"];
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
        /** AnswerRulesOut */
        AnswerRulesOut: {
            /**
             * Revision
             * @description Also the ETag; 0 until the coaching first saves.
             */
            revision: number;
            /**
             * Built In
             * @description The values used when nothing is changed.
             */
            built_in: {
                [key: string]: number | string;
            };
            /**
             * Bounds
             * @description The widest range each setting may take.
             */
            bounds: {
                [key: string]: components["schemas"]["SettingBounds"];
            };
            /**
             * Defaults
             * @description What this coaching changed.
             */
            defaults: {
                [key: string]: number | string;
            };
            /**
             * Exams
             * @description What it changed for particular exams.
             */
            exams: components["schemas"]["ExamLimits"][];
        };
        /**
         * AssetOut
         * @description A stored picture. Its bytes are read from ``/api/v1/assets/{id}/content``.
         */
        AssetOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @constant
             */
            kind: "IMAGE";
            /**
             * Content Type
             * @enum {string}
             */
            content_type: "image/png" | "image/jpeg" | "image/webp";
            /**
             * Width
             * @description Pixels, after the picture was cleaned and re-encoded
             */
            width: number;
            /** Height */
            height: number;
            /** Byte Size */
            byte_size: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
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
        /**
         * BankItem
         * @description One question as the bank shows it: the version everyone reads (the published one if there is
         *     one), with its labels. Open the question itself for the text.
         */
        BankItem: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Code */
            code: string;
            /**
             * Author Id
             * Format: uuid
             * @description Whoever started the question.
             */
            author_id: string;
            /**
             * State
             * @description The workflow state of the version shown.
             */
            state: string;
            /**
             * Version Number
             * @description 2 or more once a correction has been published.
             */
            version_number: number;
            /** Archived */
            archived: boolean;
            /**
             * Has Published
             * @description Whether a version has been published.
             */
            has_published: boolean;
            /**
             * Has Open Correction
             * @description A correction of the published version is being worked on.
             */
            has_open_correction: boolean;
            /** Question Type */
            question_type: string | null;
            /** Language */
            language: string | null;
            /** Class Id */
            class_id: string | null;
            /**
             * Subject Id
             * @description Look the name up in the coaching's syllabus.
             */
            subject_id: string | null;
            /** Chapter Id */
            chapter_id: string | null;
            /** Topic Id */
            topic_id: string | null;
            /** Primary Concept Id */
            primary_concept_id: string | null;
            /**
             * Concept Ids
             * @description The main concept and the other concepts.
             */
            concept_ids: string[];
            /**
             * Difficulty
             * @description 1 to 10.
             */
            difficulty: number | null;
            /** Bloom Level */
            bloom_level: string | null;
            /**
             * Is Pyq
             * @description A past-year question.
             */
            is_pyq: boolean;
            /** Exam Id */
            exam_id: string | null;
            /** Exam Year */
            exam_year: number | null;
            /** Has Solution */
            has_solution: boolean;
            /** Has Video */
            has_video: boolean;
            /**
             * Preview
             * @description The beginning of the question's text (about 200 characters, plain text, with equations as their LaTeX). Empty until `qbank reindex-bank` has run once after 4f.
             */
            preview: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             * @description When the question last changed, as the bank shows it.
             */
            updated_at: string;
        };
        /** BankPage */
        BankPage: {
            /** Data */
            data: components["schemas"]["BankItem"][];
            page: components["schemas"]["PageInfo"];
            /**
             * Total
             * @description How many questions match the filters, not only the ones on this page. For a search (`q`) it is how many results are shown.
             */
            total: number;
            /**
             * Truncated
             * @description A search (`q`) matched more questions than it shows: narrow it with a more specific word or a filter. Always false for the plain list, which has pages.
             * @default false
             */
            truncated: boolean;
        };
        /** Blocker */
        Blocker: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Code */
            code: string;
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
        /** ChangeOut */
        ChangeOut: {
            op: components["schemas"]["Op"];
            /**
             * Path
             * @description Where in the content: object keys and list positions, e.g. `["options", 2, "content", 0, "text"]`. Positions count as the changes are applied in the order listed.
             */
            path: (string | number)[];
            /**
             * Before
             * @description The old value (`remove` and `replace`).
             */
            before?: unknown;
            /**
             * After
             * @description The new value (`add` and `replace`).
             */
            after?: unknown;
            /**
             * Segments
             * @description For a changed text: its words, each `equal`, `insert` or `delete`. Show them as text with marks; never as HTML.
             */
            segments?: components["schemas"]["SegmentOut"][] | null;
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
        /** CreatePassage */
        CreatePassage: {
            /**
             * Content
             * @description The passage's content (schema version 1: a `title` and a `body` of content blocks). Leave it out to start an empty passage.
             */
            content?: {
                [key: string]: unknown;
            } | null;
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
        /** DecideDuplicate */
        DecideDuplicate: {
            /**
             * Other Question Id
             * Format: uuid
             */
            other_question_id: string;
            /**
             * Decision
             * @description `DUPLICATE_OF`: this question copies the other one (archive this one; nothing is merged). `NOT_DUPLICATE`: they only look alike.
             * @enum {string}
             */
            decision: "NOT_DUPLICATE" | "DUPLICATE_OF";
            /**
             * Note
             * @description Why, in a few words.
             */
            note: string;
        };
        /** DecisionOut */
        DecisionOut: {
            /**
             * Other Question Id
             * Format: uuid
             */
            other_question_id: string;
            /**
             * Decision
             * @enum {string}
             */
            decision: "NOT_DUPLICATE" | "DUPLICATE_OF";
            /** Note */
            note: string;
            /**
             * Decided By
             * Format: uuid
             */
            decided_by: string;
            /**
             * Decided At
             * Format: date-time
             */
            decided_at: string;
        };
        /** DiffOut */
        DiffOut: {
            from_revision: components["schemas"]["DiffRevision"];
            to_revision: components["schemas"]["DiffRevision"];
            /** Identical */
            identical: boolean;
            /**
             * Changes
             * @description What turns the first text into the second. Equations, pictures, tables and lists count as single items: a changed one is replaced as a whole.
             */
            changes: components["schemas"]["ChangeOut"][];
        };
        /** DiffRevision */
        DiffRevision: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Version Number */
            version_number: number;
            /**
             * Number
             * @description Counts up within the version.
             */
            number: number;
            /**
             * Frozen At
             * @description Empty for the text still being edited.
             */
            frozen_at: string | null;
        };
        /** DifficultyLevelOut */
        DifficultyLevelOut: {
            /** Level */
            level: number;
            /** Meaning */
            meaning: string;
        };
        /** DuplicateOut */
        DuplicateOut: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Code */
            code: string;
            /**
             * State
             * @description The workflow state of the version the bank shows.
             */
            state: string;
            /**
             * Match
             * @description `EXACT`: the same format, stem, options and answer (case and spacing of the prose aside; equations as written). `NEAR`: very similar text.
             * @enum {string}
             */
            match: "EXACT" | "NEAR";
            /**
             * Similarity Percent
             * @description How alike the two texts are.
             */
            similarity_percent: number;
            /**
             * Preview
             * @description The beginning of the other question's stem (plain text).
             */
            preview: string;
            /** @description The newest decision about this pair, for the text as it is now. */
            decision: components["schemas"]["DecisionOut"] | null;
        };
        /** DuplicatesOut */
        DuplicatesOut: {
            /**
             * Checked Revision Id
             * Format: uuid
             * @description The text that was checked: the one under review or published, else the working copy of a draft.
             */
            checked_revision_id: string;
            /** Version Number */
            version_number: number;
            /**
             * Data
             * @description Exact matches first, then near ones, closest first.
             */
            data: components["schemas"]["DuplicateOut"][];
            /**
             * Qc Blocked By
             * @description What stops Pass QC now: exact matches in the shared bank with no `NOT_DUPLICATE` decision, and questions this one was marked a duplicate of.
             */
            qc_blocked_by: components["schemas"]["Blocker"][];
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
        /** ExamLimits */
        ExamLimits: {
            /**
             * Exam Id
             * Format: uuid
             */
            exam_id: string;
            /** Values */
            values: {
                [key: string]: number | string;
            };
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
        /** HistoryEntry */
        HistoryEntry: {
            /** @description What happened: the start of the question, a saved checkpoint, a review step, the start of a correction, archive or restore. */
            kind: components["schemas"]["HistoryKind"];
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Actor Id
             * @description Who did it.
             */
            actor_id: string | null;
            /**
             * Version Number
             * @description The version it belongs to (1, or 2 and up for a correction); empty for archive and restore, which concern the whole question.
             */
            version_number: number | null;
            /**
             * Revision Id
             * @description The saved text the entry is about; pass it to the diff route to compare it with another.
             */
            revision_id: string | null;
            /**
             * Reasons
             * @description For a return: the reason codes chosen.
             */
            reasons: string[];
            /**
             * Note
             * @description For a return: the reviewer's note.
             */
            note: string | null;
        };
        /**
         * HistoryKind
         * @description What happened. The first and the last two are not review steps; the rest are the ``Step``
         *     names of the workflow, so a step added there is added here on purpose.
         * @enum {string}
         */
        HistoryKind: "CREATED" | "CHECKPOINT" | "SUBMIT" | "RETURN" | "PASS_QC" | "APPROVE" | "PUBLISH" | "WITHDRAW" | "START_CORRECTION" | "ARCHIVED" | "RESTORED";
        /** HistoryOut */
        HistoryOut: {
            /**
             * Data
             * @description Oldest first.
             */
            data: components["schemas"]["HistoryEntry"][];
        };
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
        /** KeysOut */
        KeysOut: {
            /**
             * Encryption Ready
             * @description False when the server has no master encryption key: keys cannot be stored until whoever runs the server sets `AI_KEYS_MASTER_KEY`.
             */
            encryption_ready: boolean;
            /** Data */
            data: components["schemas"]["ProviderKeyOut"][];
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
        /** MarkedRead */
        MarkedRead: {
            /**
             * Updated
             * @description How many unread notifications were marked as read.
             */
            updated: number;
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
        /** ModelOut */
        ModelOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            provider: components["schemas"]["Provider"];
            /** Model Id */
            model_id: string;
            /** Display Name */
            display_name: string;
            /** Enabled */
            enabled: boolean;
            /**
             * Available
             * @description False when the provider's list no longer includes it; it cannot be enabled.
             */
            available: boolean;
            /**
             * Supports Vision
             * @description Effective: the overlay, else the provider's.
             */
            supports_vision: boolean | null;
            /**
             * Supports Json
             * @description Effective: the overlay, else the provider's.
             */
            supports_json: boolean | null;
            /** Context Tokens */
            context_tokens: number | null;
            /**
             * Price In Per Mtok
             * @description US dollars per million input tokens, effective; null = unknown.
             */
            price_in_per_mtok: string | null;
            /**
             * Price Out Per Mtok
             * @description US dollars per million output tokens, effective; null = unknown.
             */
            price_out_per_mtok: string | null;
            /**
             * Price Source
             * @enum {string}
             */
            price_source: "PROVIDER" | "ADMIN" | "UNKNOWN";
            /**
             * Batch Supported
             * @description Whether Economy (batch) runs are offered: only when the admin says so.
             */
            batch_supported: boolean;
            /** Batch Discount */
            batch_discount: string | null;
            overlay: components["schemas"]["OverlayOut"];
            /**
             * Fetched At
             * Format: date-time
             */
            fetched_at: string;
            /** Revision */
            revision: number;
        };
        /** ModelsOut */
        ModelsOut: {
            /** Data */
            data: components["schemas"]["ModelOut"][];
            /** Providers */
            providers: components["schemas"]["ProviderStateOut"][];
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
        /** NotificationOut */
        NotificationOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @example REVIEW_RETURNED
             * @example QUESTION_PUBLISHED
             */
            kind: string;
            /**
             * Data
             * @description Ids and short facts (the question code, the reasons). Show as text only.
             */
            data: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Read At
             * @description Null while unread.
             */
            read_at: string | null;
        };
        /** NotificationPage */
        NotificationPage: {
            /** Data */
            data: components["schemas"]["NotificationOut"][];
            page: components["schemas"]["PageInfo"];
        };
        /**
         * Op
         * @enum {string}
         */
        Op: "add" | "remove" | "replace";
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
        /**
         * OverlayIn
         * @description Only what is sent changes. A value of `null` removes the admin's entry for that fact, so the
         *     provider's value counts again.
         */
        OverlayIn: {
            /** Supports Vision */
            supports_vision?: boolean | null;
            /** Supports Json */
            supports_json?: boolean | null;
            /** Price In */
            price_in?: number | string | null;
            /** Price Out */
            price_out?: number | string | null;
            /** Batch Supported */
            batch_supported?: boolean | null;
            /** Batch Discount */
            batch_discount?: number | string | null;
        };
        /**
         * OverlayOut
         * @description What the admin entered; null where nothing was entered (the provider's value counts).
         */
        OverlayOut: {
            /** Supports Vision */
            supports_vision: boolean | null;
            /** Supports Json */
            supports_json: boolean | null;
            /** Price In */
            price_in: string | null;
            /** Price Out */
            price_out: string | null;
            /** Batch Supported */
            batch_supported: boolean | null;
            /** Batch Discount */
            batch_discount: string | null;
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
        /** PassageCheckpointOut */
        PassageCheckpointOut: {
            /**
             * Id
             * Format: uuid
             * @description What a child question pins in `context.passage_revision_id`.
             */
            id: string;
            /** Number */
            number: number;
            /**
             * Frozen At
             * Format: date-time
             */
            frozen_at: string;
        };
        /** PassageChildList */
        PassageChildList: {
            /** Data */
            data: components["schemas"]["PassageChildOut"][];
            /** Latest Checkpoint Number */
            latest_checkpoint_number: number | null;
            /**
             * Hidden Count
             * @description Children that are other people's drafts which you may not open.
             */
            hidden_count: number;
            /**
             * Truncated
             * @description True when there are more children than this list holds (the first ones, by number, are shown).
             */
            truncated: boolean;
            /**
             * Next Number
             * @description The number for a new question: one more than the highest number among every question under the passage, including ones you may not open or that are not listed.
             */
            next_number: number;
        };
        /** PassageChildOut */
        PassageChildOut: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Code */
            code: string;
            /** Question Type */
            question_type: string | null;
            /** Archived */
            archived: boolean;
            /**
             * Ordinal
             * @description The question's number within the passage.
             */
            ordinal: number | null;
            /**
             * Pinned Checkpoint Number
             * @description The checkpoint it was written with.
             */
            pinned_checkpoint_number: number;
            /**
             * Is Current
             * @description False when the passage has a newer checkpoint than the one it pins.
             */
            is_current: boolean;
        };
        /** PassageOut */
        PassageOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Working Revision Id
             * Format: uuid
             */
            working_revision_id: string;
            /**
             * Revision
             * @description Also the ETag of the working revision.
             */
            revision: number;
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
            /** @description The newest frozen revision, which a new child question pins; none until the first checkpoint. */
            latest_checkpoint: components["schemas"]["PassageCheckpointOut"] | null;
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
        /** PassagePage */
        PassagePage: {
            /** Data */
            data: components["schemas"]["PassageSummary"][];
            page: components["schemas"]["PageInfo"];
        };
        /** PassageRevisionList */
        PassageRevisionList: {
            /** Data */
            data: components["schemas"]["PassageRevisionSummary"][];
        };
        /** PassageRevisionOut */
        PassageRevisionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: number;
            /**
             * Working
             * @description The one being edited; the others are frozen checkpoints.
             */
            working: boolean;
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
            /**
             * Passage Id
             * Format: uuid
             */
            passage_id: string;
            /**
             * Newest Id
             * Format: uuid
             * @description The newest checkpoint of the same passage (this one, if it is the newest).
             */
            newest_id: string;
            /** Newest Number */
            newest_number: number;
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
        /** PassageRevisionSummary */
        PassageRevisionSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: number;
            /**
             * Working
             * @description The one being edited; the others are frozen checkpoints.
             */
            working: boolean;
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
        /** PassageSummary */
        PassageSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Title
             * @description The working revision's title; empty until one is written.
             */
            title: string;
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
            /** Latest Checkpoint Number */
            latest_checkpoint_number: number | null;
        };
        /**
         * Provider
         * @enum {string}
         */
        Provider: "ANTHROPIC" | "OPENAI" | "GOOGLE" | "OPENROUTER";
        /** ProviderKeyOut */
        ProviderKeyOut: {
            provider: components["schemas"]["Provider"];
            /** Configured */
            configured: boolean;
            /**
             * Last4
             * @description The last four characters, so a person can tell which key is stored.
             */
            last4: string | null;
            /** Updated At */
            updated_at: string | null;
        };
        /** ProviderStateOut */
        ProviderStateOut: {
            provider: components["schemas"]["Provider"];
            /**
             * Configured
             * @description Whether the coaching has a key stored for it.
             */
            configured: boolean;
            /** Last Refreshed At */
            last_refreshed_at: string | null;
            /**
             * Last Error
             * @description The kind of failure of the last refresh (`AUTH`, `RATE_LIMITED`, `TIMEOUT`, `UNAVAILABLE`, `NO_KEY`, `KEY_UNREADABLE` ...), or null when it worked.
             */
            last_error: string | null;
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
            /** @description Where the version is in the review workflow. */
            state: components["schemas"]["State"];
            /**
             * Flow Etag
             * @description The workflow ETag, e.g. `"flow-3"`: send it in `If-Match` for every step after submit. It moves with every change of state.
             */
            flow_etag: string;
            /**
             * Allowed Steps
             * @description The steps you may take now. The screen shows exactly these.
             */
            allowed_steps: components["schemas"]["Step"][];
            /**
             * Review Revision Id
             * @description The frozen revision under review, shown instead of the working copy; null while the question is a draft or returned.
             */
            review_revision_id: string | null;
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
        /** QueueCounts */
        QueueCounts: {
            /**
             * Waiting For Qc
             * @description In review, waiting for QC.
             */
            waiting_for_qc: number;
            /**
             * Waiting For Approval
             * @description Passed QC, waiting for approval.
             */
            waiting_for_approval: number;
            /**
             * Waiting To Publish
             * @description Approved, waiting to be published.
             */
            waiting_to_publish: number;
            /**
             * Returned To Me
             * @description Questions you sent in that came back with reasons.
             */
            returned_to_me: number;
        };
        /** QueueItem */
        QueueItem: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Code */
            code: string;
            /** Question Type */
            question_type: string | null;
            /** Language */
            language: string | null;
            /**
             * Subject Id
             * @description Look the name up in the coaching's syllabus.
             */
            subject_id: string | null;
            /** Chapter Id */
            chapter_id: string | null;
            state: components["schemas"]["QueueState"];
            /**
             * Version Number
             * @description 2 or more for a correction of a published question.
             */
            version_number: number;
            /**
             * Submitted By
             * Format: uuid
             * @description Whoever sent this version in for review.
             */
            submitted_by: string;
            /**
             * Waiting Since
             * Format: date-time
             * @description When it entered its present state.
             */
            waiting_since: string;
        };
        /** QueuePage */
        QueuePage: {
            /** Data */
            data: components["schemas"]["QueueItem"][];
            page: components["schemas"]["PageInfo"];
        };
        /**
         * QueueState
         * @description The views of the queue. Nothing else is a queue state: drafts and published questions are
         *     not waiting for anyone.
         * @enum {string}
         */
        QueueState: "IN_REVIEW" | "QC_PASSED" | "APPROVED" | "CHANGES_REQUESTED";
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
        /** RefreshIn */
        RefreshIn: {
            provider: components["schemas"]["Provider"];
        };
        /** RefreshOut */
        RefreshOut: {
            /**
             * Job Id
             * Format: uuid
             */
            job_id: string;
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
        /**
         * ReturnIn
         * @description Why a question goes back to its author (E-06). The note is plain text.
         */
        ReturnIn: {
            /**
             * Reasons
             * @description One or more reasons from the fixed list.
             */
            reasons?: components["schemas"]["ReturnReason"][];
            /**
             * Note
             * @description What to fix, in at least 10 characters. Shown as text, never as markup.
             * @default
             */
            note: string;
        };
        /**
         * ReturnReason
         * @description Why a question is sent back. Stable codes, so the web can show them and later count them.
         * @enum {string}
         */
        ReturnReason: "ANSWER_WRONG" | "STATEMENT_UNCLEAR" | "OPTIONS_FLAWED" | "SOLUTION_WRONG" | "LABELS_WRONG" | "DIFFICULTY_OR_BLOOM_WRONG" | "DUPLICATE" | "FORMATTING" | "OTHER";
        /** RevisionList */
        RevisionList: {
            /** Data */
            data: components["schemas"]["RevisionSummary"][];
        };
        /** RevisionOut */
        RevisionOut: {
            /**
             * Id
             * Format: uuid
             * @description Names this saved text in the diff route.
             */
            id: string;
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
             * Id
             * Format: uuid
             * @description Names this saved text in the diff route.
             */
            id: string;
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
        /** SaveAnswerRules */
        SaveAnswerRules: {
            /**
             * Defaults
             * @description The coaching's values by setting name; leave out what is not changed.
             */
            defaults: {
                [key: string]: unknown;
            };
            /**
             * Exams
             * @description Values by exam id, each on top of the coaching's own. An exam with none is left out.
             */
            exams?: {
                [key: string]: {
                    [key: string]: unknown;
                };
            };
        };
        /** SavePassage */
        SavePassage: {
            /**
             * Content
             * @description The whole content, replacing the working revision's. Gaps are fine.
             */
            content: {
                [key: string]: unknown;
            };
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
        /**
         * SegmentKind
         * @enum {string}
         */
        SegmentKind: "equal" | "insert" | "delete";
        /** SegmentOut */
        SegmentOut: {
            kind: components["schemas"]["SegmentKind"];
            /** Text */
            text: string;
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
        /**
         * SetKey
         * @description The key as the provider gave it. Write-only: no response ever carries it.
         */
        SetKey: {
            /**
             * Key
             * Format: password
             * @description The provider's API key, as copied from the provider. It is sealed on the server and never shown again; only its last four characters are.
             */
            key: string;
        };
        /** SettingBounds */
        SettingBounds: {
            /**
             * Kind
             * @description A whole number, or a number written as text with at most two decimals.
             * @enum {string}
             */
            kind: "int" | "decimal";
            /** Low */
            low: number | string;
            /** High */
            high: number | string;
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
        /**
         * State
         * @enum {string}
         */
        State: "DRAFT" | "IN_REVIEW" | "CHANGES_REQUESTED" | "QC_PASSED" | "APPROVED" | "PUBLISHED";
        /**
         * Step
         * @enum {string}
         */
        Step: "SUBMIT" | "RETURN" | "PASS_QC" | "APPROVE" | "PUBLISH" | "WITHDRAW" | "START_CORRECTION";
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
        /** UnreadCount */
        UnreadCount: {
            /** Count */
            count: number;
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
        /** UpdateModel */
        UpdateModel: {
            /**
             * Enabled
             * @description Offer the model to faculty (true) or stop offering it (false).
             */
            enabled?: boolean | null;
            overlay?: components["schemas"]["OverlayIn"] | null;
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
    upload_image_api_v1_assets_images_post: {
        parameters: {
            query?: never;
            header?: never;
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
                    "application/json": components["schemas"]["AssetOut"];
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
            /** @description More than 10 MB or 40 megapixels (`IMAGE_TOO_LARGE`) */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not a PNG, JPEG or WebP picture that can be read (`IMAGE_INVALID`) */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many uploads, or the server is busy (`RATE_LIMITED`) */
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
    read_asset_api_v1_assets__asset_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
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
                    "application/json": components["schemas"]["AssetOut"];
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
            /** @description No such picture in your coaching (`NOT_FOUND`) */
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
    read_content_api_v1_assets__asset_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
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
                    "application/json": unknown;
                    "image/png": unknown;
                    "image/jpeg": unknown;
                    "image/webp": unknown;
                };
            };
            /** @description The browser's copy is still the current one */
            304: {
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
            /** @description Your role may not do this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such picture in your coaching (`NOT_FOUND`) */
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
            /** @description The question is archived (`QUESTION_ARCHIVED`), or it is in review or published, so its content cannot be changed (`QUESTION_NOT_EDITABLE`; withdraw it first) */
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
            /** @description The question is archived (`QUESTION_ARCHIVED`), or it is in review or published, so its content cannot be changed (`QUESTION_NOT_EDITABLE`; withdraw it first) */
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
    submit_question_api_v1_questions__question_id__submit_post: {
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
            /** @description The question has mistakes (`QUESTION_HAS_ERRORS`, with the findings) */
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
    withdraw_question_api_v1_questions__question_id__withdraw_post: {
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
    return_question_api_v1_questions__question_id__return_post: {
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
                "application/json": components["schemas"]["ReturnIn"];
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
            /** @description No reason, or a note under 10 characters (`RETURN_REASON_REQUIRED`) */
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
    pass_qc_question_api_v1_questions__question_id__pass_qc_post: {
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
            /** @description The publication checklist is not met (`PUBLICATION_CHECKLIST_FAILED`): `details.findings` lists every `error` and `incomplete` item */
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
    approve_question_api_v1_questions__question_id__approve_post: {
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
            /** @description The publication checklist is not met (`PUBLICATION_CHECKLIST_FAILED`): `details.findings` lists every `error` and `incomplete` item */
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
    publish_question_api_v1_questions__question_id__publish_post: {
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
            /** @description The question's state does not allow this step (`WORKFLOW_STEP_INVALID`, with `details.state` and `details.allowed`), or it is archived (`QUESTION_ARCHIVED`) */
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
            /** @description The publication checklist is not met (`PUBLICATION_CHECKLIST_FAILED`): `details.findings` lists every `error` and `incomplete` item */
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
    start_correction_question_api_v1_questions__question_id__start_correction_post: {
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
            /** @description The question is not published (`WORKFLOW_STEP_INVALID`), a correction is already open (`CORRECTION_ALREADY_OPEN`), or it is archived (`QUESTION_ARCHIVED`) */
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
    get_history_api_v1_questions__question_id__history_get: {
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
                    "application/json": components["schemas"]["HistoryOut"];
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
            /** @description No such question, or no such text of it, that you may read. A question or correction that is still someone else's draft is also 404 (`NOT_FOUND`) */
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
    get_diff_api_v1_questions__question_id__diff_get: {
        parameters: {
            query: {
                /** @description The older text. */
                from: string;
                /** @description The newer text. */
                to: string;
            };
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
                    "application/json": components["schemas"]["DiffOut"];
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
            /** @description No such question, or no such text of it, that you may read. A question or correction that is still someone else's draft is also 404 (`NOT_FOUND`) */
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
    get_duplicates_api_v1_questions__question_id__duplicates_get: {
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
                    "application/json": components["schemas"]["DuplicatesOut"];
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
            /** @description No such question that you may open (`NOT_FOUND`) */
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
            /** @description The check took too long and was stopped (`SEARCH_TIMED_OUT`) */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    decide_duplicate_api_v1_questions__question_id__duplicates_decisions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                question_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecideDuplicate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionOut"];
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
            /** @description You may not decide this (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question, or other question, that you may open */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The question is published (`DUPLICATE_DECISION_CLOSED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The same question, an empty question, or no note */
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
    list_passages_api_v1_passages_get: {
        parameters: {
            query?: {
                mine?: boolean;
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
                    "application/json": components["schemas"]["PassagePage"];
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
    create_passage_api_v1_passages_post: {
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
                "application/json": components["schemas"]["CreatePassage"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PassageOut"];
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
    get_passage_api_v1_passages__passage_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                passage_id: string;
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
                    "application/json": components["schemas"]["PassageOut"];
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
            /** @description No such passage that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
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
    save_working_revision_api_v1_passages__passage_id__working_revision_put: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                passage_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavePassage"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PassageOut"];
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
            /** @description No such passage that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
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
    save_checkpoint_api_v1_passages__passage_id__checkpoints_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                passage_id: string;
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
                    "application/json": components["schemas"]["PassageOut"];
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
            /** @description No such passage that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
            404: {
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
    list_revisions_api_v1_passages__passage_id__revisions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                passage_id: string;
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
                    "application/json": components["schemas"]["PassageRevisionList"];
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
            /** @description No such passage that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
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
    list_children_api_v1_passages__passage_id__children_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                passage_id: string;
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
                    "application/json": components["schemas"]["PassageChildList"];
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
            /** @description No such passage that you may open. Someone else's draft is also 404, so its existence is not given away (`NOT_FOUND`) */
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
    get_checkpoint_api_v1_passage_revisions__revision_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                revision_id: string;
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
                    "application/json": components["schemas"]["PassageRevisionOut"];
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
            /** @description No such checkpoint in your coaching (`NOT_FOUND`) */
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
    get_answer_rules_api_v1_settings_answer_rules_get: {
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
                    "application/json": components["schemas"]["AnswerRulesOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
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
    save_answer_rules_api_v1_settings_answer_rules_put: {
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
                "application/json": components["schemas"]["SaveAnswerRules"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnswerRulesOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
            403: {
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
            /** @description Some limits cannot be used; `details.problems` lists them */
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
    list_notifications_api_v1_notifications_get: {
        parameters: {
            query?: {
                /** @description Only the ones not yet read. */
                unread?: boolean;
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
                    "application/json": components["schemas"]["NotificationPage"];
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
    unread_count_api_v1_notifications_unread_count_get: {
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
                    "application/json": components["schemas"]["UnreadCount"];
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
    read_all_api_v1_notifications_read_all_post: {
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
                    "application/json": components["schemas"]["MarkedRead"];
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
    read_one_api_v1_notifications__notification_id__read_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notification_id: string;
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
                    "application/json": components["schemas"]["NotificationOut"];
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
            /** @description Refused: `ORIGIN_NOT_ALLOWED` (sent from another website), `CSRF_TOKEN_INVALID` (missing or wrong X-CSRF-Token) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not yours, or it does not exist (`NOT_FOUND`) */
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
    list_bank_api_v1_bank_questions_get: {
        parameters: {
            query?: {
                class_id?: string[] | null;
                subject_id?: string[] | null;
                chapter_id?: string[] | null;
                topic_id?: string[] | null;
                /** @description The main concept or any of the other concepts. */
                concept_id?: string[] | null;
                difficulty?: number[] | null;
                bloom_level?: string[] | null;
                question_type?: string[] | null;
                language?: string[] | null;
                exam_id?: string[] | null;
                exam_year?: number[] | null;
                state?: string[] | null;
                author_id?: string[] | null;
                is_pyq?: boolean | null;
                has_solution?: boolean | null;
                has_video?: boolean | null;
                /** @description List the archive instead. */
                archived?: boolean;
                /** @description Words to search for in the stem, options and solution. Quotes match a phrase, `-word` leaves a word out. Results are ranked, exact words first, then close words (typos); there is no next page, so give `limit` up to 100 and narrow with filters. Cannot be combined with `cursor`. */
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
                    "application/json": components["schemas"]["BankPage"];
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
            /** @description You may not use the bank (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too many searches (`RATE_LIMITED`) */
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
            /** @description The search took too long and was stopped (`SEARCH_TIMED_OUT`) */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_by_code_api_v1_bank_questions_by_code__code__get: {
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
                    "application/json": components["schemas"]["BankItem"];
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
            /** @description You may not use the bank (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such question */
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
    get_queue_api_v1_review_queue_get: {
        parameters: {
            query?: {
                state?: components["schemas"]["QueueState"] | null;
                subject_id?: string | null;
                chapter_id?: string | null;
                author_id?: string | null;
                /** @description A language code such as `en` or `hi`. */
                language?: string | null;
                /** @description Only what has waited at least this many days. */
                older_than_days?: number | null;
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
                    "application/json": components["schemas"]["QueuePage"];
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
            /** @description You hold no review grant (`PERMISSION_DENIED`) */
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
    get_counts_api_v1_review_queue_counts_get: {
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
                    "application/json": components["schemas"]["QueueCounts"];
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
            /** @description You hold no review grant (`PERMISSION_DENIED`) */
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
    list_keys_api_v1_ai_keys_get: {
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
                    "application/json": components["schemas"]["KeysOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
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
    set_key_api_v1_ai_keys__provider__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider: components["schemas"]["Provider"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetKey"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProviderKeyOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The server has no master encryption key (`AI_NOT_CONFIGURED`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Does not look like an API key (`AI_KEY_INVALID`) */
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
    delete_key_api_v1_ai_keys__provider__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider: components["schemas"]["Provider"];
            };
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No key is stored for that provider (`NOT_FOUND`) */
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
    list_models_api_v1_ai_models_get: {
        parameters: {
            query?: {
                provider?: components["schemas"]["Provider"] | null;
                enabled?: boolean | null;
                available?: boolean | null;
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
                    "application/json": components["schemas"]["ModelsOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
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
    refresh_models_api_v1_ai_models_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RefreshIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RefreshOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No key is stored for that provider (`AI_KEY_MISSING`), or the server has no master encryption key (`AI_NOT_CONFIGURED`) */
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
    update_model_api_v1_ai_models__model_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412. */
                "If-Match"?: string | null;
            };
            path: {
                model_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateModel"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelOut"];
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
            /** @description Only the Owner and admins (`PERMISSION_DENIED`) */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description No such model (`NOT_FOUND`) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description The provider no longer lists it (`AI_MODEL_UNAVAILABLE`) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Changed since you read it (`REVISION_STALE`) */
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
}
