# Security and privacy

CV Booth is intended for one user on a trusted local computer. It binds to
127.0.0.1 and provides no authentication, authorization, or user isolation.
Do not expose it to the internet or run untrusted YAML on behalf of strangers.

CV content, generated documents, and application history are private user data.
Keep them in the ignored data directory or set CVBOOTH_DATA_DIR to a private
directory outside the source checkout. Review `git diff --cached` before pushing.
An ignore rule does not protect data that has already been committed.

Avoid putting CVs, credentials, or personal application details in public reports.
Use GitHub's private vulnerability reporting feature when it is enabled. If no
private reporting channel is available, open an issue requesting a private
contact method without disclosing the vulnerability or personal data.

The app does not call an AI API. When you copy content to an AI assistant, that
service receives what you paste. Browser drafts persist until cleared, and saved
profiles and application archives persist on disk until you remove them.
