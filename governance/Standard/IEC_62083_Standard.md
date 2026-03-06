# IEC 62083 Medical Electrical Equipment - Requirements for the Safety of Radiotherapy Treatment Planning Systems

**Summary Report**

---

## 1. Scope

N/A

## 2. Normative References

N/A

## 3. Terms, Definitions and Abbreviations

N/A

---

## 4. General Requirements for Testing

### 4.1 Testing During Development

Compliance with IEC 62304 requires identification of HAZARDS, assessment of their RISKS, and appropriate verification and validation of RISK CONTROLS.

Demonstration of compliance with the requirements of this standard shall be included as part of the above processes, with explicit reference to each requirement of this standard. Compliance data shall be retained by the MANUFACTURER as a permanent record.

Each test shall include a protocol containing all the necessary input data, sufficient detail to provide for exact reproducibility, and the expected result. A statement of compliance to this standard shall be included in the technical description.

**Compliance is checked by inspection of the records of the MANUFACTURER.**

### 4.2 Testing During Installation

The MANUFACTURER shall provide an installation test document as part of the technical description that includes, as a minimum, performance of the ABSORBED DOSE distribution calculation algorithm tests given in 10.2 and tests of geometric relationships. The tests shall also demonstrate correct functioning of the RTPS hardware components and their ability to achieve predetermined results when performing TREATMENT PLANNING functions.

Due to the complexity of TREATMENT PLANNING functions and the possible use of configurations beyond those specified by the MANUFACTURERS, it is usually not possible for the MANUFACTURER to demonstrate complete fitness for use of the RTPS at time of installation.

The technical description shall provide explicit warnings to the RESPONSIBLE ORGANIZATION to add additional tests specific for the installation of the RTPS at the RESPONSIBLE ORGANIZATION.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 5. Accompanying Documents

The ACCOMPANYING DOCUMENTS shall include a technical description and the INSTRUCTIONS FOR USE, which shall contain the information as required by this standard (see Table 1 for references). This table references 36 Clauses/subclauses where they expect information to be found in "Instructions for use" or some other Technical description.

---

## 6. General Requirements for Operational Safety

### 6.1 Distances and Linear Dimensions

Distance measurements and linear dimensions shall be indicated in centimeters or in millimeters but not both. Angular dimensions shall be indicated in degrees (°). All values of distance measurements and linear and angular dimensions requested, displayed, or printed shall include their units.

**Compliance is checked by inspection of the DISPLAY and output information.**

### 6.2 Radiation Quantities

All values of radiation quantities requested, displayed or printed shall include their units. Units of radiation quantities should conform to the SI convention.

**Compliance is checked by inspection of the DISPLAY and output information.**

### 6.3 Date and Time Format

When the date is displayed or printed, correct interpretation shall not depend upon the operator's interpretation of format, and a display of the year shall be in 4 digits.

When the time is requested, displayed or printed, it shall be represented on a 24-hour clock basis, or the letters "am" and "pm" shall be appropriately included. Measurement of time shall include units (hours, minutes, seconds).

When time is entered, displayed or printed, each denomination of time shall be labeled. To prevent confusion with numbers, single-letter abbreviations of time denomination shall not be used (h, m, s). Time-sensitive functions shall be performed correctly at transitions such as year boundaries, leap years, year 2000, etc.

It shall be possible to enter, display and print time together with an indication of the time zone and, where applicable, the use of daylight saving time. The OPERATOR should have the possibility to select or de-select this option.

**Compliance is checked by testing and by inspection of the DISPLAY and output information.**

### 6.4 Protection Against Unauthorized Use

#### 6.4 a) Password Protection

A password protection feature, or the use of a key, shall be provided by the manufacturer as a means for the user to ensure that only authorized persons perform treatment planning. A means to control password access or key access shall be provided to ensure that these may be controlled by an individual designated by the user. The technical description shall describe how protection is implemented and how access is controlled.

Protection against unauthorized use shall provide for selective access for different functions so that the user can specify the levels of protection for specific operators.

**EXAMPLE:** Not all operators qualified for Treatment Planning are likely to be qualified for Brachytherapy source modeling and Equipment modeling. Also, viewing treatment plans, or printing out treatment plans, may be permitted with fewer restrictions than for treatment planning.

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 6.4 b) Network Security

Where network connection is permitted by the design, the following requirements apply:

- Access to the RTPS shall be provided only to authorized equipment or individuals who are authorized (for example, by a password under the control of the user)
- Access to equipment model, Brachytherapy source model, and patient anatomy model data, or to treatment plans (with or without absorbed dose distribution calculation) through the network shall be restricted so as to prevent unauthorized access

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 6.4 c) Copy Protection

The MANUFACTURER may employ copy protection to prevent the creation of a useable duplicate RTPS not intended by the MANUFACTURER to be used for TREATMENT PLANNING. If copy protection is employed, it shall permit backup of data. The existence of copy protection shall be stated in the INSTRUCTIONS FOR USE.

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 6.4 d) Protection Against Viruses

Protection against unauthorized changes to software or data (e.g., viruses) shall be employed. The manufacturer shall state in the INSTRUCTIONS FOR USE the means of protection employed.

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

### 6.5 Data Limits

Data elements entered by the OPERATOR or acquired from a device or network shall be compared against pre-established limits. Operation shall be prevented if the data are outside these limits unless the OPERATOR overrides a cautionary message at the time the data are found to be outside the limits.

Limits for those data elements that are entered by the OPERATOR shall be provided in the INSTRUCTIONS FOR USE and/or shall be provided as part of the error messages displayed by the RTP when these limits are exceeded.

Other consistency checks on data should also be performed as appropriate to the expected nature of the data.

For TREATMENT PLANNING performed when the OPERATOR has overridden data limits, TREATMENT PLAN reports shall include the message "CAUTION: SOME DATA ELEMENTS USED WERE OUTSIDE NORMAL RANGE" or a similar statement.

**Compliance is checked by testing and by inspection of the output information and ACCOMPANYING DOCUMENTS.**

### 6.6 Protection Against Unauthorized Modification

See Clause 13

### 6.7 Correctness of Data Transfer

#### 6.7 a) Communication Protocol

Data transferred to or from other devices shall use a communication protocol that verifies error-free transmission. The manufacturer shall specify these protocols in the technical description.

**Compliance is checked by testing and by inspection of the output information and ACCOMPANYING DOCUMENTS.**

#### 6.7 b) Data Output Format

If data are transmitted for use by another device, other than closed communication with a peripheral or a component of an integrated RTPS/delivery system that has been type tested by the MANUFACTURER, then:

- the format of the output data shall be included in the technical description, including (but not limited to) identification of all data elements, data types, and data limits;
- the data output shall include the name of the OPERATOR, the date on which the data was written, and any relevant identifiers for the PATIENT, EQUIPMENT MODEL, BRACHYTHERAPY SOURCE MODEL, PATIENT ANATOMY MODEL and TREATMENT PLAN.

**Compliance is checked by testing and by inspection of the output information and ACCOMPANYING DOCUMENTS.**

### 6.8 Coordinate Systems and Scales

It shall be possible for the OPERATOR to perform all TREATMENT PLANNING functions with the scales and coordinates of RADIOTHERAPY TREATMENT ME EQUIPMENT displayed according to the IEC 61217 convention. It should also be possible for the OPERATOR to perform all TREATMENT PLANNING functions with the scales and coordinates of ME EQUIPMENT displayed according to the customization for the particular ME EQUIPMENT performed during EQUIPMENT MODELLING.

In either case, the TREATMENT PLAN reports used for RADIOTHERAPY TREATMENT prescription shall show the scales and coordinates of ME EQUIPMENT according to the customization for the particular ME EQUIPMENT performed during EQUIPMENT MODELLING.

The method of display of scales shall be explained in the INSTRUCTIONS FOR USE.

**Compliance is checked by testing and by inspection of the DISPLAY, output information and ACCOMPANYING DOCUMENTS.**

### 6.9 Saving and Archiving Data

Means shall be provided such that an equipment model, Brachytherapy source model, treatment plan, and other data critical to proper operation can be saved while work is in progress so that it can be retrieved in the case of a system malfunction.

Means shall be provided for archiving data onto a separate medium from the primary storage, such that it can be retrieved in the case of a failure of the data storage device or complete RTPS.

**Compliance is checked by testing.**

---

## 7. Radiotherapy Treatment Equipment and Brachytherapy Source Modeling

### 7.1 Equipment Model

#### 7.1 a) Radiation Quality Information

An EQUIPMENT MODEL shall contain all information required to identify the available RADIATION QUALITY from the RADIOTHERAPY ME EQUIPMENT in the required detail to prevent ambiguity. For each RADIATION QUALITY available, this shall include, but not be limited to:

- RADIATION QUALITY
- NOMINAL ENERGY
- where applicable ABSORBED DOSE profiles and DEPTH DOSE distribution data measured under, or validated for, conditions that permit modeling in human tissue.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 b) Available Ranges

An equipment model shall include the available ranges of the BLD, gantry motion, and all other motions and geometric factors that are pertinent to the treatment planning process.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 c) Beam Modifying Devices

An equipment model shall include all pertinent data for radiation beam modifying devices that are to be useable during the treatment planning process, such as wedge filters, electron beam applicators, and multi-element BLD. The data shall be in the form of exact values or bounded ranges (for example, for allowed radiation field size). All such values shall be displayed for the operator to review during the equipment modeling process.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 d) Device Locations

When appropriate, an equipment model shall specify all available locations, relative to the radiation source, of blocking trays, compensators, or other customizable radiation beam modifying devices.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 e) Customizable Parameters

Where the EQUIPMENT MODELLING process is not confined to particular ME EQUIPMENT for which the direction of motion and reference position of motions of ME EQUIPMENT parts are known, then the EQUIPMENT MODELLING process shall permit these parameters to be customizable for each EQUIPMENT MODELLED. While the parameters are being customized, the DISPLAY shall clearly indicate the direction of view from which the OPERATOR is observing the ME EQUIPMENT.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 f) IEC 61217 Convention

It shall be possible for the operator to select the convention established by IEC 61217.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 g) Data Input Documentation

The means by which ME EQUIPMENT data are input into the RTPS, and the complete data set required, shall be described in the INSTRUCTIONS FOR USE.

The MANUFACTURER shall state in the INSTRUCTIONS FOR USE the minimum data required for the RTPS to perform to the SPECIFIED accuracy, and shall also include any pertinent instructions or precautions concerning the quality of the data to be entered.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.1 h) No Default Values

Data to be entered by the OPERATOR shall not default to any value without confirmation by the OPERATOR.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

### 7.2 Brachytherapy Source Model

#### 7.2 a) Source Model Content

A BRACHYTHERAPY SOURCE MODEL shall contain:

- parameters describing the ABSORBED DOSE profiles for a nominal source strength (e.g., a TG43 model) measured under, or validated for, conditions that permit modeling in human tissue
- a reference to the source of these parameters
- RADIOACTIVE HALF LIFE of the RADIONUCLIDE
- any conversion factors used by the RTPS to convert the source strength of the sources to other units.

#### 7.2 b) Data Input Requirements

The means by which data are input into the RTPS, and the complete data set required, shall be described in the INSTRUCTIONS FOR USE.

The MANUFACTURER shall state in the INSTRUCTIONS FOR USE the minimum data required for the RTPS to perform to the SPECIFIED accuracy, and shall also include any pertinent instructions or precautions concerning the quality of the data to be entered.

#### 7.2 c) No Default Values

Data to be entered by the OPERATOR shall not default to any value without confirmation by the OPERATOR.

**NOTE:** For electronic brachytherapy equipment the requirements of 7.1 for an EQUIPMENT MODEL are valid. The requirements of 7.1 b) and f) may not be applicable to this type of equipment.

### 7.3 Dosimetric Information

#### 7.3 a) Modeled Dosimetric Volume

Where an EQUIPMENT MODEL or a BRACHYTHERAPY SOURCE MODEL is based on dosimetric data entered by the OPERATOR during the modeling process, the dimensions of the volume to which the dosimetric data apply (modeled dosimetric volume) shall be displayed during the modeling process.

#### 7.3 b) Dose Outside Modeled Volume

The ABSORBED DOSE RATE outside the modeled dosimetric volume shall either be set to zero or extrapolated. Extrapolated data shall be non-negative and shall:

- be set to a SPECIFIC constant relative ABSORBED DOSE RATE; or
- be determined by a SPECIFIED mathematical formula dependent on a SPECIFIED distance parameter.

The OPERATOR shall be informed through a message, or other means, of the method used to estimate the ABSORBED DOSE outside the modeled volume during EQUIPMENT MODELLING or TREATMENT PLANNING. The method used to estimate the ABSORBED DOSE outside the modeled volume shall be explained in the technical description.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 7.3 c) Transmission Ratios

Where TRANSMISSION RATIOS or other parameters for RADIATION BEAM modifying devices that are required for ABSORBED DOSE distribution calculation are to be entered, these values shall be displayed along with the physical parameters for the beam modifiers for the OPERATOR to review during the EQUIPMENT MODELLING PROCESS.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

### 7.4 Model Acceptance

#### 7.4 a) Completion Requirements

It shall be possible to save an equipment model as "complete" after creation or modification only when the operator has acknowledged that the data and parameters in the model have been reviewed and are correct, and that dosimetric data has been confirmed through alternative calculations, comparison to published data, independent review, or other appropriate means.

**Compliance is checked by the tests.**

#### 7.4 b) Review Capabilities

Means shall be provided so that the operator may review all pertinent data prior to saving the equipment model or brachytherapy source model as "complete". Graphical representation of the data should be provided where applicable.

**Compliance is checked by the tests.**

#### 7.4 c) Model Identification

When the equipment model or brachytherapy source model is accepted and saved, it shall be saved along with the date of acceptance, along with the operator's identification, and under a separate name from other saved models, unless the operator overrides a cautionary message.

**Compliance is checked by the tests.**

### 7.5 Equipment Model, Brachytherapy Source Model Deletion

It shall not be possible to delete an equipment model or brachytherapy source model unless the operator has received and overridden a cautionary message advising that the model should be archived prior to being deleted.

---

## 8. Anatomy Modeling

### 8.1 Data Acquisition

#### 8.1 a) Data Entry Documentation

The means by which anatomy modeling data are entered into the RTPS shall be described in the Instructions For Use.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.1 b) Image Parameter Validation

When image data are acquired from an imaging device (CT, MRI, etc.), and there are adjustments on the imaging device that affect the suitability for use of the images for TREATMENT PLANNING, then for each such parameter one of the following shall apply:

1. if the parameter is acquired with the images, then the parameter shall be checked for each image; if it is not acceptable, then:
   - the RTPS shall provide a means of compensating for the parameter, or
   - the use of the images for TREATMENT PLANNING shall not be permitted.

2. if the parameter is not acquired with the images, the OPERATOR shall be required to confirm the correctness of the parameter by other means.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.1 c) Patient Data Confirmation

Images or other PATIENT data acquired from another device shall be confirmed by the OPERATOR as belonging to a particular PATIENT, and as being otherwise acceptable for use, unless at least the PATIENT name and a unique PATIENT ID of the acquired data from the other device correspond with the PATIENT name and unique PATIENT ID of the PATIENT selected by the OPERATOR.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.1 d) Inhomogeneity Correction

If inhomogeneity correction is performed based on CT image data or similar data acquired from another device and the data are not directly useable without a conversion factor or curve:

- if any data element is outside the conversion curve, either inhomogeneity correction shall not be executed or a warning message shall be displayed, and
- the OPERATOR shall be required to confirm that the calibration curve is appropriate for those images, unless this can be automatically confirmed through information acquired with the images;
- the manufacturer shall specify in the ACCOMPANYING DOCUMENTS the physical property required by the TPS (e.g., electron density, mass density).

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

### 8.2 Coordinate Systems and Scales

#### 8.2 a) Patient Coordinate System

The positions of applied RADIATION BEAMS, BRACHYTHERAPY RADIOACTIVE SOURCES and dosimetric information shall be displayed in relation to a PATIENT coordinate system, such as the convention illustrated in ICRU Report 42 (1987). An illustration of the PATIENT coordinate system shall be given in the INSTRUCTIONS FOR USE.

**NOTE:** At the time this standard was created, IEC 61217 did not include a PATIENT coordinate system, although inclusion of one had been proposed. It is expected that the next edition of this standard will refer to IEC 61217 for the PATIENT coordinate system which will have been included in its revision.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.2 b) Display Requirements

All DISPLAYS of PATIENT anatomy shall be accompanied by:

- scales to indicate PATIENT dimensions
- coordinates that establish the image position relative to the origin of axes of the PATIENT coordinate system, and
- indications such as the left and right side of the PATIENT, anterior or posterior, that are necessary to completely define the orientation of the PATIENT.

**Compliance is checked by the tests.**

#### 8.2 c) Alternative Coordinate Systems

Any coordinate systems used, other than those defined in IEC 61217, shall be described explicitly and illustrated in the INSTRUCTIONS FOR USE, including their relationship to the PATIENT coordinate system. A DISPLAY or printout of data for which parameters are SPECIFIED in one of these systems shall identify the coordinate system to which it is related.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.2 d) Patient Orientation

The operator shall be required to enter or confirm parameters that completely determine the patient orientation.

**Compliance is checked by the tests.**

### 8.3 Contouring Regions of Interest

Where segmentation of anatomical structures or other regions of interest is required in order to prepare for planning and Absorbed Dose distribution calculation, then:

#### 8.3 a) Viewing Segmented Structures

It shall be possible for the operator to view the segmented structures or regions of interest.

**Compliance is checked by the tests.**

#### 8.3 b) Modifying Segmentation

It shall be possible for the operator to modify segmentation and to toggle the display of segmented features on or off.

**Compliance is checked by the tests.**

#### 8.3 c) Overlapping Volume Handling

If bulk density assignment is based on segmentation of anatomical features or other regions of interest, and two such features have an overlapping volume, then either:

- there shall be a hierarchy of bulk density assignments, described in the INSTRUCTIONS FOR USE, that ensures that bulk density of the overlapping volume is unambiguously assigned, or
- ABSORBED DOSE distribution calculation shall be inhibited until the OPERATOR has modified the segmentation, or otherwise unambiguously assigned a bulk density to the overlapping volume

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 8.3 d) Feature Identification

Segmented features shall be identified and the corresponding bulk densities indicated. This information shall be included on the treatment plan report.

**Compliance is checked by the tests.**

### 8.4 Patient Anatomy Model Acceptance

#### 8.4 a) Completion Requirements

It shall not be possible to save a PATIENT ANATOMY MODEL as "complete", unless:

- the PATIENT orientation has been established according to 8.2 d)
- the image cross-checking or OPERATOR acceptance has been performed according to 8.1 b)
- the assignment of images belonging to the correct PATIENT has been confirmed according to 8.1 c)
- the OPERATOR has confirmed that the images, including any segmentation performed, have been reviewed and are acceptable, and belong to the intended PATIENT.

**Compliance is checked by the tests.**

#### 8.4 b) Model Identification

When the PATIENT ANATOMY MODEL is saved, it shall be saved:

- along with the date and time it was saved
- along with the name and unique identifier for the PATIENT
- along with the OPERATOR's identification, and
- under a separate name from saved PATIENT ANATOMY MODELS accepted as "complete" according to 8.4 a), unless the OPERATOR overrides a cautionary message.

**Compliance is checked by the tests.**

### 8.5 Patient Anatomy Model Deletion

It shall not be possible to delete a patient ANATOMY model until the operator has received and overridden a cautionary message advising that the patient anatomy model should be archived prior to deletion.

**Compliance is checked by the tests.**

---

## 9. Treatment Planning

### 9.1 General Requirements

#### 9.1 a) Incomplete Model Warning

When an incomplete equipment model, brachytherapy source model or patient anatomy model is in use, the operator shall be required to override a cautionary message that states the model is incomplete.

**Compliance is checked by the tests.**

#### 9.1 b) Exceeding Equipment Limits

If it is possible for the OPERATOR to specify a RADIATION BEAM dimension or position that is not within the available range SPECIFIED for the BEAM LIMITING DEVICE, BEAM APPLICATOR, or RADIATION BEAM modifying device as SPECIFIED in the selected EQUIPMENT MODEL, then an additional message or parameter shall be provided so that it is clear to the OPERATOR that the maximum size has been exceeded, and to what extent.

**EXAMPLES:** exceeding these limits may be desirable for a large-field "beam's-eye view" or for a large-field digitally reconstructed RADIOGRAM.

**Compliance is checked by the tests.**

### 9.2 Treatment Plan Preparation

#### 9.2 a) Maximum Number Limits

The manufacturer shall specify in the Instructions For Use the maximum number of radiation beams, brachytherapy radioactive sources, or other radiation-generating equipment, that should not be exceeded in any one treatment plan.

These limiting numbers should be either hard-coded to prevent operation outside of these bounds, or result in cautionary display.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

#### 9.2 b) Combining Treatment Plans

Where two or more TREATMENT PLANS are combined, the combined TREATMENT PLANS shall use the identical PATIENT ANATOMY MODEL, or the OPERATOR shall be requested to confirm that the PATIENT ANATOMY MODELS are compatible. The algorithm for combining TREATMENT PLANS shall meet the requirements of 10.2.

**Compliance is checked by the tests.**

### 9.3 Treatment Plan Identification

When a treatment plan is saved, it shall be saved:

- Along with the time and date when it was saved
- Along with the Operator's Identification
- Along with the identifier of the Equipment Model or Brachytherapy Source Model used
- Along with the version number of the software under which it was created
- Along with the identifier of the Patient and the Patient Anatomy Model used, and
- under a separate name from other saved Treatment Plans, unless the Operator overrides a cautionary message

**Compliance is checked by testing.**

### 9.4 Treatment Plan Deletion

It shall not be possible to delete a Treatment Plan unless the operator has received and overridden a cautionary message advising that the Treatment Plan should be archived prior to deletion.

**Compliance is checked by testing.**

### 9.5 Electronic Signatures

#### 9.5 a) Usage Instructions

Where design allows a Treatment Plan to be reviewed or approved by entry of a name or an electronic signature, the Instructions For Use shall describe how these features are to be properly and safely used.

#### 9.5 b) Signature Removal on Modification

If a Treatment Plan is approved by means of an electronic signature, any modification to the Treatment Plan shall result in removal (or other effective cancellation) of the electronic signature. The Treatment Plan history after an electronic signature is applied shall be traceable.

**Compliance is checked by testing.**

---

## 10. Absorbed Dose Distribution Calculation

### 10.1 Algorithms Used

#### 10.1 a) Algorithm Description

A description of all algorithms used for calculation shall be included in the technical description. This shall include a description of the factors accounted for by the algorithm, the mathematical equations forming the basis of the calculation, and the limits applied to all variables used in the equations. References to literature shall be provided for published algorithms.

**NOTE:** "All algorithms" in this subclause includes supplemental calculations such as digitally reconstructed RADIOGRAMS, BRACHYTHERAPY RADIATION SOURCE reconstruction algorithms, optimization algorithms and radiobiological effect calculations. It also includes all algorithms that affect calculation through identification of the TARGET VOLUME or other structures, such as automatic contouring or other automatic structure identification techniques, and automatic margining of a region of interest.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 10.1 b) Algorithm Selection Guidance

Where a choice of algorithms is provided for a particular calculation, the INSTRUCTIONS FOR USE shall discuss the relative advantages and disadvantages of the different algorithms with respect to clinical situations.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 10.1 c) BLD Modeling

The technical description shall include a description of how all BLDs are modeled during calculation. This description shall include both calculation of TRANSMISSION through radiation beam modifiers and calculation in the PENUMBRA region.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

### 10.2 Algorithm Accuracy and Testing

#### 10.2 a) Accuracy Statement

For each algorithm used, the technical description shall state the accuracy of the algorithm relative to measured data for at least one set of pre-defined conditions. The pre-defined conditions shall be chosen to simulate the conditions for normal use. Where pre-defined conditions are available in a published report or standard, these should be used.

The technical description shall include all description and data necessary for the RESPONSIBLE ORGANIZATION to reproduce the pre-defined conditions, or suitable references if these conditions are publicly available. It shall also include test procedures that permit convenient testing by the RESPONSIBLE ORGANIZATION to show that the expected results are achieved with the provided input data.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 10.2 b) Mathematical Correctness

Each algorithm shall be implemented in such a way that it will not produce a mathematically incorrect result under the most extreme allowed ranges of input variables.

**Compliance is checked by tests performed under the conditions specified by b).**

#### 10.2 c) Interpolation/Extrapolation Error

Where dose estimation is based on values at specific points from which the dosimetric values at other points are interpolated or extrapolated, then the theoretical dosimetric error introduced by the interpolation or extrapolation shall be described in the technical description for typical TREATMENT PLANNING conditions. Where the OPERATOR can make choices that will increase or decrease this effect, the choices made by the OPERATOR shall be DISPLAYED and shall be included in the TREATMENT PLAN report. Cautionary notices shall also be provided.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 10.2 d) Accuracy Limitations

The Instructions For Use shall provide cautionary notes for the operator concerning the limitations of accuracy of the Absorbed Dose distribution calculations for situations where the expected level of accuracy may not apply.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

#### 10.2 e) Quantitative Results

For each algorithm employed, the technical description shall include a graph, plot, or table of data that shows quantitative results for a typical application.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 11. Treatment Plan Report

### 11.1 Incomplete Treatment Plan Report

If a Treatment Plan report is generated from, or using, an equipment model, brachytherapy source model, or patient anatomy model that has not been saved as "complete", then the message "Equipment Model incomplete", "Brachytherapy Source Model incomplete", or "Patient Anatomy Model incomplete", shall be included in the Treatment Plan report.

**Compliance is checked by testing.**

### 11.2 Information on the Treatment Plan Report

In addition to all applicable Absorbed Dose distribution, isodose lines, Dose Monitor Units and irradiation time information, each Treatment Plan report shall include as a minimum:

- The version number of the RTPS software
- Patient name and unique identifier
- If an equipment model is used:
  - the unique identifier of the ME EQUIPMENT and of the EQUIPMENT MODEL
  - its RADIATION QUALITY
  - all parameters, such as RADIATION FIELD size and GANTRY angle, required to define the characteristics of size, shape, and position of each RADIATION BEAM displayed on the TREATMENT PLAN report
  - the identifier, dimension and dosimetric parameters of all WEDGE FILTERS, ELECTRON BEAM APPLICATORS, RADIATION BEAM shaping blocks, compensators, or other BLD in addition to the primary BLDs, multi-element BLDs, programmable wedge filters
  - the date the EQUIPMENT MODEL was saved
- If a BRACHYTHERAPY RADIOACTIVE SOURCE is used:
  - the unique identifier of the BRACHYTHERAPY RADIOACTIVE SOURCE
  - its source strength
  - the identifier of the BRACHYTHERAPY applicator
  - the date the BRACHYTHERAPY SOURCE MODEL was saved
- The unique identifiers of the PATIENT ANATOMY MODEL, and TREATMENT PLAN
- The date and time that the treatment Plan was saved
- The messages, if applicable, required by 6.5, 7.3, 8.1, 9.1.a, 9.1.b and 11.1
- The contour and bulk density identifiers, if applicable, required by 8.3
- The method of RADIATION BEAM weighting, isodose distribution normalization, and the reference point selected
- The chosen calculation algorithm, if a choice was available
- The choices made by the OPERATOR that affect calculation accuracy as required by 10.2
- Operator identification
- Reviewer's name or electronic signature, if the design permits or requires review or approval of the Treatment Plan electronically
- Signature block for the approver's name, signature and date

Key identifying elements shall be included on each page of the Treatment Plan report. These shall include, as a minimum, the patient name, patient identifier, the date and time of the Treatment Plan generation.

**Compliance is checked by inspection of the output information.**

### 11.3 Transmitted Treatment Plan Information

Where Treatment Plan information is transmitted to other devices or locations, then the operator shall be required to confirm that all necessary approvals have been obtained for the Treatment Plan information.

**Compliance is checked by testing.**

---

## 12. General Hardware Diagnostics

The system shall perform a diagnostic check of the hardware during the power-up sequence. The diagnostic checks should also be designed to execute periodically or upon operator demand. This test shall be designed to determine, to the greatest extent possible, that the computer CPU, memory and the peripheral hardware are all functioning correctly. The tests performed shall be described in the technical description.

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 13. Data and Code

Executable program code, Equipment Model data, and Brachytherapy Source Model data shall have checksum or other equivalent protection that ensures that they will not be used if modified through a hardware fault, virus, accidentally during servicing, or other unauthorized manner. The manufacturer shall provide instruction to the operator for restoring correct operation, either on the display or in the Instructions For Use.

If alteration or deletion of program code or data is possible using utilities of the computer operating system or other utilities that are outside of the control of the manufacturer, then the manufacturer shall provide a cautionary notice in the Instructions For Use advising the operator not to use the facilities for any purpose related to the program code or data, other than procedures specified by the manufacturer in the Instructions For Use.

**Compliance is checked by testing and by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 14. Human Errors in Software Design

### 14 a) IEC 62304 Compliance

The requirements for software development process and RISK MANAGEMENT as defined in IEC 62304 shall apply during the development process. These include, but are not limited to:

- documented validation of all RISK CONTROLS
- maintaining the required RISK MANAGEMENT FILE, and
- ensuring that all significant problems prior to release for clinical use are investigated and resolved.

**Compliance is checked by examining system documentation to the requirements of IEC 62304.**

### 14 b) Error Reporting

The MANUFACTURER shall provide, in the INSTRUCTIONS FOR USE, a means by which the RESPONSIBLE ORGANIZATION can report errors in software operation that are observed during use or testing.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 15. Changes in Software Versions

The following requirements apply when a new version of software is provided to the user by the manufacturer.

### 15 a) Installation Instructions

Instructions shall be provided in the Instructions For Use for installation of the new version, and any tests that are required to determine that the installation was successful.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

### 15 b) Data Compatibility

If use of data from the previous version could cause incorrect results:

- the design shall convert the data to the new format, or
- the design shall prevent use of the data, or
- the INSTRUCTIONS FOR USE accompanying the new version shall provide explicit warnings to the RESPONSIBLE ORGANIZATION, and shall provide all necessary instructions to ensure that the operation of the system continues to be safe.

**Compliance is checked by the tests and by inspection of the ACCOMPANYING DOCUMENTS.**

### 15 c) Data Protection

If the installation of a new version of software release may delete or corrupt the Equipment Model, Brachytherapy Source Model, or the Patient Anatomy Model data, the operator shall be warned and provided an opportunity to archive the data before deletion or corruption occurs.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

### 15 d) Archived Plan Retrieval

The Instructions For Use shall provide instruction on how to retrieve and to complete/modify a Treatment Plan that has been archived with the previous software version.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

---

## 16. User Errors

The RTPS shall comply with the requirements of IEC 62366.

The INSTRUCTIONS FOR USE shall provide comprehensive instructions to the RESPONSIBLE ORGANIZATION of all information needed for safe operation, including, but not limited to, the SPECIFIC information in other clauses and subclauses of this standard.

The INSTRUCTIONS FOR USE shall provide cautionary notices to the RESPONSIBLE ORGANIZATION that convey the following messages:

- that all TREATMENT PLAN reports shall be approved by a QUALIFIED PERSON before the information in them is used for RADIOTHERAPY TREATMENT purposes,
- that the RESPONSIBLE ORGANIZATION shall ensure that individuals authorized to perform TREATMENT PLANNING functions are appropriately trained for the functions they perform, and
- that the OPERATOR shall always be aware that the quality of the output depends critically on the quality of the input data, and any irregularities or uncertainties about input data units, identification, or quality of any other nature shall be thoroughly investigated before the data are used.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

---

## ANNEXES

### Annex A - General Requirements

#### A.1.1 Overview

This standard is concerned principally with operational features and other aspects of RTPS software required for safe operation. It shall be supplemented by, or be supplemental to, an appropriate hardware safety standard, to which the MANUFACTURER shall additionally demonstrate compliance.

If the MANUFACTURER does not supply the hardware required to operate the RTPS, the technical description shall contain a warning to the RESPONSIBLE ORGANIZATION to install the RTPS software on hardware that complies with an appropriate hardware safety standard.

Below are general descriptions of some of the available standards and some comments about their applicability. The list is not meant to be comprehensive, and it is the responsibility of the MANUFACTURER to identify and select appropriate standards, including their most recent revisions and amendments. The MANUFACTURER may use standards other than those listed where analysis shows them to be also appropriate.

#### A.1.2 IEC 60950-1, Information Technology Equipment – Safety – Part 1: General Requirements

IEC 60950-1 applies to a range of INFORMATION TECHNOLOGY EQUIPMENT as identified in its subclause 1.1.1.

If an RTPS uses general purpose computer hardware and peripherals, and is not used with direct connections to a PATIENT, then IEC 60950-1 is a pertinent standard.

**Compliance is checked by testing and inspection, as required by the appropriate standards, and by inspection of the ACCOMPANYING DOCUMENTS for identification of the standards.**

#### A.1.3 IEC 60601-1, Medical Electrical Equipment – Part 1: General Requirements for Basic Safety and Essential Performance

IEC 60601-1 is the general standard for the BASIC SAFETY of MEDICAL ELECTRICAL EQUIPMENT. If the RTPS hardware is used in the presence of PATIENTS, or is integrated with hardware used in the presence of PATIENTS, then IEC 60601-1 may be an appropriate standard to use for hardware safety considerations, and this standard can be read as a complement for an RTPS.

**Compliance is checked by testing and inspection, as required by the appropriate standards, and by inspection of the ACCOMPANYING DOCUMENTS for identification of the standards.**

#### A.1.4 Electromagnetic Compatibility Standards

IEC 61000-4-1, IEC 61000-4-2, IEC 61000-4-3, IEC 61000-4-4, Electromagnetic compatibility (EMC) – Part 4: Testing and measurement techniques; IEC 60601-1-2, Medical electrical equipment – Part 1-2: General requirements for basic safety and essential performance – Collateral standard (to IEC 60601-1): Electromagnetic compatibility – Requirements and tests.

These standards address ELECTROMAGNETIC COMPATIBILITY test requirements and/or methods for INFORMATION TECHNOLOGY EQUIPMENT and for MEDICAL ELECTRICAL EQUIPMENT. Applicability will depend on the nature of the hardware and the environment in which it is to be used. In most cases, an RTPS will use general-purpose commercial computer hardware for use in an environment appropriate to such equipment.

The computer MANUFACTURER may have certified the equipment to one of these standards. If the computer is of custom construction, or is integrated with ME EQUIPMENT that has connections to a PATIENT, further analysis will likely be required to determine which standards apply.

The MANUFACTURER shall state in the technical description all hardware safety standards with which the RTPS complies.

**Compliance is checked by testing and inspection, as required by the appropriate standards, and by inspection of the ACCOMPANYING DOCUMENTS for identification of the standards.**

### A.2 Completeness of Hardware Safety

Demonstration of hardware safety shall include, but not necessarily be limited to, the following potential HAZARDS:

- electric shock
- fire
- physical injury
- ELECTROMAGNETIC COMPATIBILITY, and
- emitted RADIATION exceeding authorized limits

**Compliance is checked by inspection of the hardware safety standards chosen for inclusion of the required HAZARDS, and by supplemental testing and inspection as needed.**

### A.3 Completeness of Accompanying Documents

The INSTRUCTIONS FOR USE and technical description shall include all pertinent information needed to ship, install, operate and service the hardware safely, including, but not necessarily limited to packaging, shipping and storage conditions, installation instructions, operating environment (including temperature, humidity and electrical services); INSTRUCTIONS FOR USE and precautions, and servicing instructions and precautions.

**Compliance is checked by inspection of the ACCOMPANYING DOCUMENTS.**

### Annex ZA - Normative References to International Publications

The following referenced documents are indispensable for the application of this document. For dated references, only the edition cited applies. For undated references, the latest edition of the referenced document (including any amendments) applies.

### Annex ZZ - Coverage of Essential Requirements of EC Directives

This European Standard has been prepared under a mandate given to CENELEC by the European Commission and the European Free Trade Association and within its scope the standard covers all relevant essential requirements as given in Annex I of the EC Directive 93/42/EEC. Compliance with this standard provides one means of conformity with the specified essential requirements of the Directive concerned.

### Annex B - Imported and Exported Data

**NOTE:** The RESPONSIBLE ORGANIZATION retains the responsibility to ensure that all personnel responsible for TREATMENT PLANNING are appropriately qualified, and that the complete TREATMENT PLANS are appropriately reviewed and approved.

Concerning output data, where this is meant for general use rather than for device-to-device direct links, this standard requires that the MANUFACTURER provide detailed information about the nature and format of the output data in the technical description. Further checks and verifications will then be the responsibility of the devices that use this data as input.

A major cause of problems when data are passed between devices is the set of assumptions that are necessarily made when the data are received as regards data type, limits, and meaning of individual data elements. Some progress has been made in recent years in establishing standard communication formats for images, and other work for RADIOTHERAPY parameters is in progress. MANUFACTURERS should use these standards as they become available in order to minimize the potential for errors.

---

**Document Generated:** 2026-01-02  
**CompliantFlow Project**
