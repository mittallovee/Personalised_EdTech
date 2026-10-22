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
         * @description Not called by our web app. On success the browser is redirected to the home page with a new session, as after `POST /auth/login`; for linking, to `/profile?google=linked`. Every failure (an unknown or replayed flow, a Google account nobody linked or already linked, no access any more, Google refusing) is the same redirect, to `/login?google=failed` (to `/profile?google=failed` when linking), so nothing is revealed.
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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountLinkOut */
        AccountLinkOut: {
            /**
             * Token
             * @description Shown only now. The web app turns it into `<app address>/activate#<token>`. Any earlier link of the same kind for this member stops working.
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
        /** CreatedOrganization */
        CreatedOrganization: {
            organization: components["schemas"]["OrganizationOut"];
            owner: components["schemas"]["InvitedOwner"];
            /** @description A new activation link for the Owner. Null only when a retried request finds that the Owner has already activated their account. */
            activation: components["schemas"]["ActivationLink"] | null;
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
}
