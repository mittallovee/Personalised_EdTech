# Turning on "Sign in with Google"

Until you do this, the app works with email and password only, and no Google button appears anywhere.
The setup is a one-time job: about 15 minutes to try it yourself with your own Google account, and
longer if you then publish it for everyone (step 2 explains why). It costs nothing and needs no
payment details.

> **Google renames its screens now and then.** The steps below say what to look for by purpose. If a
> menu is called something slightly different, look for the same idea.

## What this gives people

- **Sign in with Google** on the sign-in page, for people who linked a Google account.
- **Continue with Google instead** on the activation page, so a newly invited person can skip
  choosing a password.
- **Profile → Link Google account**, for people who already have a password. They type their
  password again, then choose the Google account.

An account is recognised by Google's permanent account ID, **never by email address**. Someone with
the same email but a different Google account cannot get in. Signing in with Google never creates an
account: people must be invited first.

## 1. Create a project at Google

1. Open <https://console.cloud.google.com/> and sign in with the Google account that should *own*
   this setup (use a long-lived account, not a personal one you might close).
2. At the top, open the project picker, choose **New project**, name it `Question Bank`, and create
   it. Make sure it is selected afterwards.

## 2. Describe the app (the "consent screen")

This is the screen people see at Google ("Question Bank wants to know your email address").

1. In the menu, find **APIs & Services → OAuth consent screen** (newer consoles call it **Google Auth
   Platform**).
2. **App name:** `Question Bank` (or your coaching's name). **User support email:** your email.
   **Developer contact:** your email.
3. **Audience / user type:**
   - Choose **External** (works for any Google account). Choose **Internal** only if everyone who
     will sign in belongs to one Google Workspace organisation you control.
4. **Scopes:** the app asks only for `openid` and `email`, the basic ones. If the console asks you
   to add scopes, add those two and nothing else. Basic scopes do not need Google's scope review.
5. **Publishing status:**
   - While the status is **Testing**, only the email addresses you list under **Test users** can use
     it (up to 100), and none of the checks below apply. That is fine while you try it yourself: add
     your own Google account.
   - When you are ready for faculty, choose **Publish app** (**In production**). **Google may then
     ask you to verify the app's branding** (its name and logo): typically a homepage and privacy
     policy address on a domain you can prove you own. This is separate from the scope review, and
     Google decides what it requires and changes the rules from time to time. Read the current
     rules before you publish: <https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification>.
     (This guide was written without being able to check that page, so treat it as the authority,
     including for what people see if the branding is not verified.)

## 3. Create the sign-in credentials

1. Go to **APIs & Services → Credentials** (or **Google Auth Platform → Clients**) and choose
   **Create credentials → OAuth client ID** (**Create client**).
2. **Application type:** **Web application**. **Name:** `Question Bank web`.
3. **Authorized redirect URIs:** add one line **for every address people use to open the app**. The
   path is always `/api/v1/auth/google/callback`, and it must match **exactly** (letters, `https`
   vs `http`, no trailing slash):

   | Where | Redirect URI |
   |---|---|
   | On your PC | `http://localhost:3000/api/v1/auth/google/callback` |
   | Through your domain | `https://qb.loveemittal.online/api/v1/auth/google/callback` |

   Leave **Authorized JavaScript origins** empty: the app does not use Google's browser scripts.
4. Create it. Google shows a **Client ID** (ends in `.apps.googleusercontent.com`) and a **Client
   secret**. Copy both somewhere safe for the next step. The secret is a password: anyone who has it
   can pretend to be your app.

## 4. Give them to the app

In the `.env` file next to `compose.yaml` (it is never committed to git):

```env
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-the-secret-you-copied
```

The app must also know the web address(es) people use. If you use the domain as well, this line
should already be there from [remote-access.md](./remote-access.md) (keep the single quotes):

```env
ALLOWED_ORIGINS='["http://localhost:3000","https://qb.loveemittal.online"]'
```

Then restart the API so it reads them:

```bash
docker compose up -d --force-recreate api
```

Both values must be set; setting only one stops the API at start-up with a clear message.

## 5. Check that it works

1. Open `http://localhost:3000/api/v1/auth/methods` in the browser. It should say
   `{"password":true,"google":true}`. If `google` is `false`, the values did not reach the API
   (see the table below).
2. Open the sign-in page: **Sign in with Google** appears under the password form.
3. Link your own account first: sign in with your password, open **Profile**, type your password,
   and choose **Link Google account**. Choose your Google account (if the app is in Testing, it must
   be a listed test user). You should land back on **Profile** with "Your Google account is linked".
4. Sign out, then **Sign in with Google**. You should be in.
5. To try activation: invite someone (**Users & grants**), open their activation link in a private
   window and choose **Continue with Google instead**.

## When something goes wrong

| What you see | Usual cause and fix |
|---|---|
| No Google button; `/api/v1/auth/methods` says `"google":false` | `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not both set, or the API was not restarted after editing `.env`. |
| Google shows **Error 400: redirect_uri_mismatch** | The redirect URI in step 3 does not match the address in the browser's address bar. Compare character by character (`http` vs `https`, the domain, and the path). Add the missing one. |
| Google shows **Access blocked** or "has not completed verification" | The app is in **Testing** and your account is not a test user. Add it under **Test users**, or publish the app. |
| The app says "We could not sign you in with Google" | The Google account is not linked to any account here (sign in with your password and link it on **Profile**); or that Google account is linked to someone else; or the account lost access (removed, or the coaching is suspended). The app deliberately never says which. |
| While activating: "We could not finish setting up your account with Google" | The person cancelled at Google, took more than 10 minutes, or the link was used, replaced or expired meanwhile. They open the link the admin sent them again (a cancelled attempt does not use it up); if it no longer works, the admin makes a new one. |
| "We could not link your Google account" | The Google account already belongs to another person here, or you took too long (the sign-in expires after 10 minutes), or you were signed out meanwhile. Try again. |
| Linking asks for the password and refuses it | Wrong password. Repeated wrong passwords lock the account for a while, just as at sign-in. |
| The request to start fails with "web address is not allowed" | The address in the browser is not in `ALLOWED_ORIGINS`. |

## Good to know

- **What the app stores:** Google's account ID, and the email address Google reported when the
  account was linked (shown on **Profile**, for information only). It never receives your Google
  password, and asks for no access to your mail, files or contacts.
- **If the secret leaks** (committed by mistake, pasted in chat): open the client in the Google
  console, create a new secret, update `.env`, restart, and delete the old secret. Rotate it on
  purpose now and then as well.
- **Turning it off again:** empty both values in `.env` and restart the API. People keep their
  linked accounts, and password sign-in is unaffected. **But anyone who has no password can no longer
  sign in at all while Google is off.** That means everyone who was activated with *Continue with
  Google* and never got a password. The Profile page shows such a person "Password: Not set". Before
  you turn Google off, give each of them a password: **Users & grants → Password-reset link**, and
  send it to them. Or keep Google on. (The members list does not yet mark who signs in with Google
  only; if in doubt, make a reset link for everyone who was invited while Google was on.)
- **Nobody can lock themselves out by unlinking:** a Google account can be unlinked only while a
  password remains. A person activated with Google has no password, so they cannot unlink; an admin
  can make them a **password-reset link** if they want one.
- **Cloud later (M7):** repeat step 3 for the real address of the deployed app, and keep the secret in
  the hosting provider's secret store instead of a `.env` file.
