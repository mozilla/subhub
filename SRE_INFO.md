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
[New Relic APM](https://rpm.newrelic.com/accounts/2239138/applications/153639011)

### SSL Expiry checks in New Relic
[dev.fxa.mozilla-subhub.app](https://synthetics.newrelic.com/accounts/2239138/monitors/4ad6af80-a18e-44c2-8da9-a2b2ec50997d)

[prod.fxa.mozilla-subhub.app](https://synthetics.newrelic.com/accounts/2239138/monitors/c44b53f1-8fd4-4f0c-a844-5a1e82eb7560)

[qa.fxa.mozilla-subhub.app](https://synthetics.newrelic.com/accounts/2239138/monitors/a36774d9-4017-49b7-bd3d-e19c317b5e6c)

[stage.fxa.mozilla-subhub.app](https://synthetics.newrelic.com/accounts/2239138/monitors/41da8e65-daa0-4bdf-809f-11b679bccf28)

## Cloud Account
AWS account mozilla-subhub 903937621340
