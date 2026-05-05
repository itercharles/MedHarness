# Risk Management Plan

**Document ID:** risk_management_plan
**Standard:** ISO 14971:2019
**Status:** Draft

## 1. Scope

This risk management plan covers the {{project_name}} software system across its full lifecycle: development, release, post-market maintenance, and retirement. Lifecycle phases in scope: design, implementation, verification, validation, release, and post-production.

## 2. Risk Management Responsibilities

A designated risk manager is responsible for overseeing all risk management activities. All personnel performing risk analysis, risk control, or risk review activities must demonstrate competence through relevant education, training, or experience.

## 3. Risk Acceptability Criteria

Risk acceptability is determined using a 5×5 severity-probability matrix:

| | Negligible (1) | Minor (2) | Serious (3) | Critical (4) | Catastrophic (5) |
|---|---|---|---|---|---|
| Improbable (1) | Acceptable | Acceptable | Acceptable | ALARP | Unacceptable |
| Remote (2) | Acceptable | Acceptable | ALARP | Unacceptable | Unacceptable |
| Occasional (3) | Acceptable | ALARP | Unacceptable | Unacceptable | Unacceptable |
| Probable (4) | ALARP | Unacceptable | Unacceptable | Unacceptable | Unacceptable |
| Frequent (5) | Unacceptable | Unacceptable | Unacceptable | Unacceptable | Unacceptable |

**ALARP:** As Low As Reasonably Practicable — risk control required; residual risk must be justified by benefit.

## 4. Intended Use and Reasonably Foreseeable Misuse

**Intended use:** {{project_name}} is used by medical device software development teams to manage Design History Files and generate audit evidence for regulatory submissions.

**Intended users:** Software engineers, quality engineers, regulatory affairs specialists.

**Reasonably foreseeable misuse:**
- Using automated check output as a substitute for regulatory review without human oversight
- Relying on automated checks as the sole verification of design completeness
- Operating without understanding the limitations of automated analysis

## 5. Risk Management Activities

Risk management activities are tracked in the DHF as RISK items (hazard identification, estimation, evaluation) and RCM items (risk controls, implementation, verification). All activities reference this plan.

## 6. Risk Management File

The risk management file comprises all RISK and RCM items in the DHF, this plan, and the risk management report generated at each release review.
