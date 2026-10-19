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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
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
        /** LiveStatus */
        LiveStatus: {
            /**
             * Status
             * @constant
             */
            status: "ok";
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
        };
        /** MyOrganization */
        MyOrganization: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Role */
            role: string;
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
}
