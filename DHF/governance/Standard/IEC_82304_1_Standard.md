# IEC 82304-1:2016 Health Software - Part 1: General Requirements for Product Safety

---

## 1. Scope

This document applies to the safety and security of health software products designed to operate on general computing platforms and intended to be placed on the market without dedicated hardware, and its life cycle processes.

## 2. Normative References

The following documents are referred to in the text in such a way that some or all of their content constitutes requirements of this document. For dated references, only the edition cited applies. For undated references, the latest edition of the referenced document (including any amendments) applies.

## 3. Terms and Definitions

For the purposes of this document, the terms and definitions given in IEC 60601-1, IEC 62304, ISO 14971 and the following apply.

---

## 4. Health Software Product Requirements

### 4.1 General Requirements and Initial Risk Assessment

**The MANUFACTURER shall determine and document:**

**a)** the INTENDED USE for the HEALTH SOFTWARE PRODUCT, including the intended USER profile and the intended operational environment;

**b)** the characteristics related to the SAFETY and/or SECURITY of the HEALTH SOFTWARE PRODUCT, identification of HAZARDS and estimation of the associated RISK(S). As applicable, this includes situations where the HEALTH SOFTWARE PRODUCT can be configured and/or supports interfaces to other products;

**c)** the need for RISK CONTROL measures for estimated RISKS that are considered unacceptable.

### 4.2 Health Software Product Use Requirements

**The MANUFACTURER shall determine and document:**

**a)** requirements that address the INTENDED USE;

**b)** interface requirements, including USER interface requirements where applicable;

**c)** requirements for immunity from or susceptibility to unintended influence by other software using the same hardware resources;

**d)** privacy and SECURITY requirements addressing areas such as authorised use, person authentication, health data integrity and authenticity, and protection against malicious intent;

**e)** requirements for ACCOMPANYING DOCUMENTS such as instructions for use (see 7.2.2);

**f)** requirements to support:
1. upgrades from previous versions, including maintaining data integrity, and compatibility with prior versions,
2. rollback to the previous version after upgrade,
3. timely SECURITY patches and updates,
4. software distribution mechanism that ensures integrity of installation,
5. decommissioning, irreversible deletion, transfer and/or retention of data;

**g)** requirements derived from applicable regulation, including rules for protected information.

### 4.3 Verification of Health Software Product Use Requirements

**The MANUFACTURER shall verify that the HEALTH SOFTWARE PRODUCT use requirements are:**

**a)** defined and documented as input for system requirements;

**b)** such that the MANUFACTURER is able to meet the defined use requirements.

The results of the VERIFICATION shall be recorded.

### 4.4 Updating Health Software Product Use Requirements

The MANUFACTURER shall ensure that the HEALTH SOFTWARE PRODUCT use requirements are updated as appropriate, e.g. as a result of HEALTH SOFTWARE PRODUCT use requirements VERIFICATION (see 4.3) or as a result of VALIDATION.

### 4.5 System Requirements

The MANUFACTURER shall specify and document the system requirements for the HEALTH SOFTWARE PRODUCT. These requirements shall include the functionality for INTENDED USE and, as applicable:

**a)** inter-operability;

**b)** localization and language support;

**c)** RISK CONTROL measures that have to be implemented in the HEALTH SOFTWARE PRODUCT at system level, based on the initial RISK ASSESSMENT of 4.1;

**d)** USER interface specification;

**e)** requirements on the software and hardware platforms for the HEALTH SOFTWARE PRODUCT to function as expected under expected load, and with required performance levels;

**f)** features that allow for SECURITY compromises to be detected, recognized, logged, timed, and acted upon during normal use;

**g)** features that protect essential functions, even when the software SECURITY has been compromised;

**h)** methods for retention and recovery of product configuration by an authenticated privileged USER.

The HEALTH SOFTWARE PRODUCT system requirements shall meet the HEALTH SOFTWARE PRODUCT use requirements (see 4.2).

### 4.6 Verification of System Requirements

**The MANUFACTURER shall verify that the system requirements:**

**a)** do not contradict each other;

**b)** are expressed in terms that avoid ambiguity;

**c)** are stated in terms that permit the establishment of test criteria and performance of tests to determine that test criteria have been met; and

**d)** can be uniquely identified.

The results of the VERIFICATION shall be recorded.

### 4.7 Updating Health Software Product System Requirements

The MANUFACTURER shall ensure that the HEALTH SOFTWARE PRODUCT system requirements are updated as appropriate, e.g. as a result of modification on the HEALTH SOFTWARE PRODUCT use requirements, as a result of system requirement VERIFICATION (see 4.6), or as a result of applying 5.2 of IEC 62304:2006 and IEC 62304:2006/AMD1:2015 (software requirements analysis).

---

## 5. Health Software – Software Life Cycle Processes

The system requirements for the HEALTH SOFTWARE PRODUCT established in 4.5 shall be used as primary design input for the life cycle process of the HEALTH SOFTWARE PRODUCT.

The requirements in 4.2, 4.3, Clause 5, Clause 6, Clause 7, Clause 8 and Clause 9 of IEC 62304:2006 and IEC 62304/AMD1:2015 shall apply to the HEALTH SOFTWARE in addition to the other requirements of this document.

IEC 62304:2006 and IEC 62304/AMD1:2015 normatively references ISO 14971:2007. It is recognized that the MANUFACTURER might not be able to follow all the process steps identified in ISO 14971:2007 for each constituent component of the HEALTH SOFTWARE, such as proprietary components, subsystems of non-healthcare origin, and legacy software. In this case, the MANUFACTURER shall take account of the RESIDUAL RISKS and implement RISK CONTROLS around those found to be unacceptable.

---

## 6. Health Software Product Validation

### 6.1 Validation Plan

The MANUFACTURER shall establish a VALIDATION plan addressing all HEALTH SOFTWARE PRODUCT use requirements established in 4.2.

**In the VALIDATION plan, the MANUFACTURER shall:**

**a)** identify the VALIDATION scope and the corresponding VALIDATION activities;

**b)** identify the constraints that potentially limit the feasibility of VALIDATION activities;

**c)** select appropriate VALIDATION methods, input information, and associated acceptance criteria for successful VALIDATION;

**d)** identify the enabling systems or services such as operating environment(s), including hardware and software platforms, needed to support VALIDATION;

**e)** specify the required qualification of the VALIDATION personnel; where training is required, this shall be completed before starting the VALIDATION;

**f)** define the appropriate level of independence of the VALIDATION team from the design team.

### 6.2 Performing Validation

**The MANUFACTURER shall confirm readiness for VALIDATION once:**

**a)** the VALIDATION plan has been established;

**b)** the VALIDATION team has been set up with the appropriately qualified personnel; and

**c)** as appropriate, development life cycle phases as required by Clause 5 have been completed for those parts of the HEALTH SOFTWARE PRODUCT subject to VALIDATION.

The VALIDATION team shall perform the VALIDATION activities in the intended operational environment(s) according to the VALIDATION plan of 6.1.

Where deviations from the VALIDATION plan are deemed necessary, they shall be justified in the VALIDATION report.

When ANOMALIES are found in the HEALTH SOFTWARE PRODUCT during VALIDATION, these shall be resolved through a problem resolution process according to Clause 9 of IEC 62304/AMD1:2015.

Where this problem resolution process results in modification of the HEALTH SOFTWARE PRODUCT, the affected part of the VALIDATION shall be repeated, taking into account the extent of the modification.

### 6.3 Validation Report

The VALIDATION team shall develop the VALIDATION report for the HEALTH SOFTWARE PRODUCT subject to VALIDATION.

**The VALIDATION report shall provide evidence that:**

**a)** the VALIDATION results are traceable to the HEALTH SOFTWARE PRODUCT use requirements, taken as input;

**b)** the HEALTH SOFTWARE PRODUCT meets the use requirements established in 4.2; and

**c)** the RESIDUAL RISK of the HEALTH SOFTWARE PRODUCT remains acceptable.

The VALIDATION report shall document the VALIDATION conditions and the results of the VALIDATION activities.

If, during VALIDATION, ANOMALIES were identified in the HEALTH SOFTWARE PRODUCT, these shall be listed in the VALIDATION report.

The VALIDATION report shall list the members of the VALIDATION team (name, affiliation, function).

The VALIDATION report shall include a summary of the VALIDATION results, and the conclusion that the HEALTH SOFTWARE PRODUCT is validated for the INTENDED USE, based on the use requirements.

---

## 7. Health Software Product Identification and Accompanying Documents

### 7.1 Identification

A HEALTH SOFTWARE PRODUCT shall be identified with the name or trademark of the MANUFACTURER, a product name, or type reference, and a unique version identifier such as a revision level or date of release/issue.

The identification of the HEALTH SOFTWARE PRODUCT shall be accessible to the USER when using the HEALTH SOFTWARE.

### 7.2 Accompanying Documents

#### 7.2.1 General

The MANUFACTURER shall make available ACCOMPANYING DOCUMENTS for the HEALTH SOFTWARE to allow the USER and/or RESPONSIBLE ORGANIZATION to implement and use the HEALTH SOFTWARE PRODUCT as intended.

**The ACCOMPANYING DOCUMENTS shall include:**

**a)** the name and contact information, including the website, of the MANUFACTURER;

**b)** the HEALTH SOFTWARE PRODUCT identification (see 7.1);

**c)** the version identifier(s) of the HEALTH SOFTWARE PRODUCT(S) such as revision level(s) or date(s) of release/issue, necessary to identify the HEALTH SOFTWARE PRODUCT(S) to which it applies;

**d)** the version identifier of the ACCOMPANYING DOCUMENTS such as revision level or date of release/issue;

**e)** the instructions for use (see 7.2.2); and

**f)** the technical description (see 7.2.3).

The ACCOMPANYING DOCUMENTS may include software release notes and an indication of typical installation environments.

The ACCOMPANYING DOCUMENTS shall specify any special skills, training and knowledge required of the intended USER or the RESPONSIBLE ORGANIZATION, any restrictions on locations or environments in which the HEALTH SOFTWARE PRODUCT can be used, and, as applicable, any system interface, software platforms and tools, and hardware requirements or restrictions.

The ACCOMPANYING DOCUMENTS shall be provided at a level consistent with the education, training and any special needs of the person(s) for whom they are intended.

#### 7.2.2 Instructions for Use

##### 7.2.2.1 General

The instructions for use shall document all that is necessary for proper operation of the HEALTH SOFTWARE PRODUCT, including installation instructions where appropriate.

If applicable, the instructions for use shall specify restrictions on an IT-NETWORK on which the HEALTH SOFTWARE PRODUCT is intended to be used (see 7.2.3.2).

##### 7.2.2.2 Health Software Description

**The instructions for use shall contain:**

**a)** the INTENDED USE of the HEALTH SOFTWARE PRODUCT as defined by the MANUFACTURER;

**b)** a brief description of the HEALTH SOFTWARE PRODUCT, including the essential functions of the HEALTH SOFTWARE PRODUCT;

**c)** any operational SECURITY options for the use of the HEALTH SOFTWARE; and

**d)** any known technical issues, limitations, disclaimer, or contraindication(s) to the use of the HEALTH SOFTWARE PRODUCT.

##### 7.2.2.3 Warnings and Notices for Safety and/or Security

The instructions for use shall list all warnings and notices for SAFETY and/or SECURITY related to the use of the HEALTH SOFTWARE PRODUCT and explain or expand them when they are not self-explanatory.

General warnings and notices for SAFETY and/or SECURITY should be placed in a specifically identified section of the instructions for use. A warning or a notice for SAFETY or for SECURITY that applies only to a specific instruction or action should precede the instruction to which it applies.

##### 7.2.2.4 Installation

**The instructions for use shall contain:**

**a)** a statement whether the installation can be done by the USER or shall be done by or with the assistance of the MANUFACTURER, or by an authorised person;

**b)** the system requirements for the software and hardware platforms intended to execute the HEALTH SOFTWARE;

**c)** operational SECURITY options for the HEALTH SOFTWARE to be set at installation time;

**d)** any critical dependencies on other applications;

**e)** the configuration requirements;

**f)** the system interface requirements (both required and optional);

**g)** the details of the supported software platforms; and

**h)** the installation instructions or a reference to where the installation instructions are to be found.

##### 7.2.2.5 Start-up Procedure

The instructions for use shall contain the necessary information for the USER to bring the HEALTH SOFTWARE into operation.

##### 7.2.2.6 Shutdown Procedure

The instructions for use shall contain the necessary information for the USER to safely shut down the operation of the HEALTH SOFTWARE.

##### 7.2.2.7 Operating Instructions

The instructions for use shall contain all information necessary to operate the HEALTH SOFTWARE. This shall include explanation of the function of controls, displays and signals and the sequence of operation.

The instructions for use shall explain the meanings of figures, symbols, warning statements and abbreviations.

##### 7.2.2.8 Messages

The instructions for use shall list all system messages, error messages and fault messages that are generated, unless these messages are self-explanatory.

The list shall include an explanation of messages including important causes, and possible action(s) by the USER, if any, that are necessary to resolve the situation indicated by the message.

##### 7.2.2.9 Decommissioning and Disposal of Health Software

The instructions for use shall contain all information necessary for the USER or the RESPONSIBLE ORGANIZATION to safely decommission and dispose of the HEALTH SOFTWARE. This shall include, where appropriate, safeguarding personal and health-related data in connection with SECURITY and privacy.

##### 7.2.2.10 Reference to the Technical Description

The instructions for use shall contain the technical description (see 7.2.3) or a reference to where the technical description can be found.

#### 7.2.3 Technical Description

##### 7.2.3.1 General

The technical description shall provide all data that is essential for safe and secure operation, transport and storage, and measures or conditions necessary for installing the HEALTH SOFTWARE, and preparing it for use. This shall include:

**a)** the system requirements for the software and hardware platforms intended to execute the HEALTH SOFTWARE;

**b)** the details of the supported software platforms;

**c)** the permissible environmental conditions for transport and storage of the media containing the HEALTH SOFTWARE;

**d)** all characteristics of the HEALTH SOFTWARE, including range(s), accuracy, and precision of the displayed values or an indication where they can be found;

**e)** any special installation requirements or restrictions;

**f)** any maintenance requirements, such as log files to be checked and possibly cleared, database maintenance, and change of storage media;

**g)** any technical SECURITY options that can be configured within the HEALTH SOFTWARE PRODUCT, and that are available to the RESPONSIBLE ORGANIZATION. Such SECURITY may include:
1. configuration options, e.g. minimum list of network ports and computer services that are required.
2. software options, e.g. turn on encryption settings, change default login credentials.
3. operational options, e.g. auditing and logging management settings.

**h)** a description of what the software does when a failure to maintain SECURITY is detected. The description shall include any impact to patient care, data or clinical workflow.

The MANUFACTURER shall provide instructions in the technical description for the USER and/or the RESPONSIBLE ORGANIZATION on how to deal with changes of the hardware and software platforms (e.g., with patches/updates of antivirus/firewall software, system libraries, firmware, and others), and how to select appropriate platform settings to support the SECURITY goals and SECURITY capabilities.

##### 7.2.3.2 Health Software Intended to be Used in an IT-Network

The scope of the IT-NETWORK may include supporting IT infrastructure or systems not explicitly intended to be used in a healthcare setting. See 3.9.

If the HEALTH SOFTWARE is intended to be used in an IT-NETWORK that is outside the control of the HEALTH SOFTWARE MANUFACTURER, the MANUFACTURER shall provide, as part of the technical description, instructions necessary for this use, including but not limited to the following:

**a)** the characteristics and configuration of the IT-NETWORK required for the HEALTH SOFTWARE to achieve its purpose;

**b)** the technical specifications of the IT-NETWORK necessary for the HEALTH SOFTWARE to achieve its purpose, including SECURITY specifications and protection against malware (short for malicious software) or similar;

**c)** the intended information flow between the HEALTH SOFTWARE and other software or systems using the IT-NETWORK.

The MANUFACTURER shall include in the technical description a list of the HAZARDOUS SITUATIONS resulting from a failure of the IT-NETWORK to provide the characteristics and services required for the purpose of the HEALTH SOFTWARE when using that IT-NETWORK.

**In the technical description, the MANUFACTURER shall inform the RESPONSIBLE ORGANIZATION that:**

**a)** execution of the HEALTH SOFTWARE on an IT-NETWORK could result in previously unidentified RISKS to patients, USERS or third parties;

**b)** the RESPONSIBLE ORGANIZATION is advised to identify, analyze, evaluate and control these RISKS;

**c)** subsequent changes to the IT-NETWORK could introduce new RISKS and require additional analysis; and

**d)** changes to the IT-NETWORK include:
1. changes in IT-NETWORK configuration;
2. addition of items (hardware and/or software platforms or software applications) to the IT-NETWORK;
3. removal of items from the IT-NETWORK;
4. update of hardware and/or software platforms or software applications on the IT-NETWORK; and
5. upgrade of hardware and/or software platforms or software applications on the IT-NETWORK.

---

## 8. Post-market Activities for the Health Software Product

### 8.1 General

According to Clause 1, this document covers the entire life cycle of HEALTH SOFTWARE. Within its life cycle, HEALTH SOFTWARE is likely to undergo SOFTWARE MAINTENANCE and, at the end, decommissioning and disposal. Subclause 4.2 addresses use requirements to be implemented and validated prior to making the product available for use; those requirements include decommissioning and disposal of a HEALTH SOFTWARE PRODUCT. When this document is used for compliance purposes, only the post-market aspects that relate to product design and development apply.

### 8.2 Software Maintenance

Where the MANUFACTURER decides that SOFTWARE MAINTENANCE is relevant or necessary, for instance, due to detected errors that can have an impact on SAFETY and/or SECURITY, the MANUFACTURER shall develop the modification of the HEALTH SOFTWARE PRODUCT in compliance with this document (see Clause 5).

### 8.3 Re-Validation

The MANUFACTURER shall ensure re-VALIDATION takes place of the parts of the HEALTH SOFTWARE PRODUCT that have been affected by the SOFTWARE MAINTENANCE, taking into account the extent of the modification.

The MANUFACTURER shall update the VALIDATION plan accordingly.

The MANUFACTURER shall ensure that the modified version of the HEALTH SOFTWARE functions with any hardware and software platform that is claimed to be supported.

### 8.4 Post-market Communication on the Health Software Product

The MANUFACTURER shall inform USERS of the HEALTH SOFTWARE PRODUCT and impacted RESPONSIBLE ORGANIZATIONS about SECURITY vulnerabilities the MANUFACTURER has become aware of, and of changes in regulatory requirements that impact the use of the HEALTH SOFTWARE PRODUCT.

In the case of SOFTWARE MAINTENANCE, the MANUFACTURER shall make information available to USERS and to the RESPONSIBLE ORGANIZATIONS of the availability of the updated version of the HEALTH SOFTWARE PRODUCT, and provide information about the following, where appropriate:

**a)** new features;

**b)** corrected errors or faults;

**c)** any impact on SAFETY and/or SECURITY of the modified software;

**d)** updates in the HEALTH SOFTWARE identification (see 7.1);

**e)** updates in the ACCOMPANYING DOCUMENTS (see 7.2).

The decision of the USER or the RESPONSIBLE ORGANIZATION whether to install the modified version of the HEALTH SOFTWARE should be based on SAFETY and/or SECURITY impacts of the modifications.

Where the modified HEALTH SOFTWARE PRODUCT has a positive impact on the SAFETY and/or SECURITY of the HEALTH SOFTWARE, MANUFACTURER may advise the USERS and the RESPONSIBLE ORGANIZATIONS to replace their version in the short term.

### 8.5 Decommissioning and Disposal of the Health Software Product

The USER or the RESPONSIBLE ORGANIZATION shall be able to safely decommission and dispose of the HEALTH SOFTWARE PRODUCT at the end of its useful life, including, where appropriate, safeguarding personal and health-related data in connection with SECURITY and privacy.

The HEALTH SOFTWARE shall provide this function consistent with the applicable use requirements as specified in 4.2.

---

**Document Generated:** 2026-01-02  
**CompliantFlow Project**
