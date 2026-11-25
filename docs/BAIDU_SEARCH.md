# Baidu search
APIHz documents a free standard endpoint with shared public demonstration credentials 88888888 / 88888888. To opt in, export APIHZ_PUBLIC_DEMO=1. For private credentials set APIHZ_ID and APIHZ_KEY in the shell; never commit credentials. Set APIHZ_ALLOW_FALLBACK=1 to allow the configured APIHz source after a successful empty result from BAIDU_SEARCH_URL. If no gateway is configured, explicitly opting into APIHz enables it directly.
Run python -m nail_media.service --tasks config/baidu-smoke.json --once.
The API returns image URLs only, not original publisher attribution; records retain the Baidu search homepage as a platform reference, not a verified original source. No download or publication permission is inferred. No direct no-key Baidu endpoint has been verified.
