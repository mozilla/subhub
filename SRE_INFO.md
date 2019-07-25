# SRE Info
This is the SRE_INFO.md file which should be found in the root of any source code that is
administered by the Mozilla IT SRE team. We are available on #it-sre on slack.

## Infra Access
[SRE aws-vault setup](https://mana.mozilla.org/wiki/display/SRE/aws-vault)

[SRE account guide](https://mana.mozilla.org/wiki/display/SRE/AWS+Account+access+guide)

[SRE AWS accounts](https://github.com/mozilla-it/itsre-accounts/blob/master/accounts/mozilla-itsre/terraform.tfvars#L5)

## Secrets
Secrets in this project all reside in AWS Secrets Manager. There is one set of secrets for each
environment: prod, stage, qa, dev.  These secrets are loaded as environment variables via the
subhub/secrets.py file and then generally used via the env loading mechanism in suhub/cfg.py which
uses decouple to load them as fields.

## Source Repos
[subhub](https://github.com/mozilla/subhub)

## Monitoring

### SSL Expiry checks in New Relic

## Cloud Account
AWS account mozilla-subhub 903937621340
