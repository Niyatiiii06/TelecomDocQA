# Evaluation set review checklist

For each question: open the PDF in `data/raw/` at the page shown, read the section, and check that
(1) the section really answers the question, (2) the reference answer matches what it says, and
(3) the question is clear. Tick the box if it's fine; otherwise write what's wrong underneath.
When you're done, tell Claude which questions need fixing, and the rest will be marked `verified`.

Page numbers are the PDF viewer's page numbers (not the numbers printed on the page).

### q01: Which two types of NG-RAN node exist and how are they connected to the 5G core?
- **TS 38.300 §4.1** Overall Architecture (pp. 25-28)

> **Reference answer:** An NG-RAN node is either a gNB, which provides NR user plane and control plane terminations towards the UE, or an ng-eNB, which provides E-UTRA terminations towards the UE. gNBs and ng-eNBs are interconnected via the Xn interface and connect to the 5GC via the NG interfaces: to the AMF over NG-C and to the UPF over NG-U.

- [ ] OK

### q02: What waveform does NR use in the uplink?
- **TS 38.300 §5.1** Waveform, numerology and frame structure (pp. 40-41)

> **Reference answer:** The uplink uses conventional OFDM with a cyclic prefix (CP-OFDM) with a transform precoding function performing DFT spreading that can be enabled or disabled. The downlink uses CP-OFDM.

- [ ] OK

### q03: What does the SDAP layer do?
- **TS 38.300 §6.5** SDAP Sublayer (p. 60)

> **Reference answer:** SDAP maps QoS flows to data radio bearers and marks the QoS flow ID (QFI) in both downlink and uplink packets. A single SDAP entity is configured for each PDU session.

- [ ] OK

### q04: What is a bandwidth part and why is it used?
- **TS 38.300 §6.10** Bandwidth Adaptation (pp. 62-63)

> **Reference answer:** A bandwidth part (BWP) is a subset of the total cell bandwidth. With Bandwidth Adaptation the UE's receive and transmit bandwidth need not be as large as the cell's and can be adjusted: shrunk during low activity to save power, moved in frequency for scheduling flexibility, or changed in subcarrier spacing for different services. It works by configuring BWPs and telling the UE which one is active.

- [ ] OK

### q05: List the main functions of the PDCP sublayer.
- **TS 38.300 §6.4.1** Services and Functions (pp. 59-60)

> **Reference answer:** PDCP transfers user and control plane data, maintains PDCP sequence numbers, performs header compression (ROHC, EHC) and uplink data compression, ciphering and deciphering, integrity protection and verification, timer-based SDU discard, routing for split bearers, duplication, reordering and in-order delivery, out-of-order delivery and duplicate discarding.

- [ ] OK

### q06: What are the three RLC transmission modes and which one is used for SRB0?
- **TS 38.300 §6.3** RLC Sublayer (pp. 58-59)

> **Reference answer:** RLC supports Transparent Mode (TM), Unacknowledged Mode (UM) and Acknowledged Mode (AM). TM is used for SRB0, paging and broadcast system information; other SRBs use AM, and DRBs use UM or AM.

- [ ] OK

### q07: How does paging differ between RRC_IDLE and RRC_INACTIVE?
- **TS 38.300 §7.2** Protocol States (pp. 67-68)

> **Reference answer:** In RRC_IDLE, paging for mobile terminated data is initiated by the 5GC, with DRX for CN paging configured by NAS. In RRC_INACTIVE, paging is initiated by NG-RAN (RAN paging), the RAN-based notification area is managed by NG-RAN, and the 5GC-NG-RAN connection for the UE is kept.

- [ ] OK

### q08: What events trigger the random access procedure in NR?
- **TS 38.300 §9.2.6** Random Access Procedure (pp. 109-112)

> **Reference answer:** Random access is triggered by initial access from RRC_IDLE, RRC connection re-establishment, DL or UL data arrival when UL synchronisation is lost, UL data arrival when no PUCCH resources for SR are available, handover (unless RACH-less), SR failure, an explicit request by RRC on synchronous reconfiguration, and RRC connection resume from RRC_INACTIVE, among others.

- [ ] OK

### q09: How does a UE detect radio link problems while in RRC_CONNECTED?
- **TS 38.300 §9.2.7** Radio Link Failure (pp. 112-113)

> **Reference answer:** The UE performs Radio Link Monitoring (RLM) in the active BWP based on reference signals (SSB or CSI-RS) and signal quality thresholds configured by the network.

- [ ] OK

### q10: When does a UE declare beam failure?
- **TS 38.300 §9.2.8** Beam failure detection and recovery (pp. 113-114)

> **Reference answer:** The gNB configures beam failure detection reference signals (SSB or CSI-RS), and the UE declares beam failure when the number of beam failure instance indications from the physical layer reaches a configured threshold before a configured timer expires.

- [ ] OK

### q11: What is the purpose of the DRX inactivity timer?
- **TS 38.300 §11** UE Power Saving (pp. 126-127)

> **Reference answer:** The inactivity timer is how long the UE waits to successfully decode a PDCCH after the last successful PDCCH decoding; if it fails to decode one, it can go back to sleep. The UE restarts the timer after a successful PDCCH decoding.

- [ ] OK

### q12: How does NR deliver earthquake and tsunami warnings to phones?
- **TS 38.300 §16.4** Public Warning System (p. 159)

> **Reference answer:** NR supports public warning systems through system information broadcast: it schedules and broadcasts the warning messages and pages the UE to indicate a warning is being broadcast. ETWS notifications can be primary (short) or secondary (detailed).

- [ ] OK

### q13: What is the role of HARQ in NR?
- **TS 38.300 §6.2.4** HARQ (p. 58)
- **TS 38.300 §6.2.1** Services and Functions (p. 57)

> **Reference answer:** HARQ ensures delivery between peer entities at Layer 1 and provides error correction in the MAC layer (one HARQ entity per cell with carrier aggregation). A HARQ process supports one transport block, or one or more with spatial multiplexing.

- [ ] OK

### q14: What is Supplementary Uplink and how is it different from aggregated uplink?
- **TS 38.300 §5.4.2** Supplementary Uplink (p. 49)
- **TS 38.300 §6.9** Supplementary Uplink (p. 62)

> **Reference answer:** Supplementary Uplink (SUL) is an additional uplink carrier configured together with a UL/DL carrier pair or a TDD carrier. Unlike aggregated uplink, the UE can be scheduled on either the SUL or the uplink of the supplemented carrier, but not on both at the same time.

- [ ] OK

### q15: Can a UE send data without leaving RRC_INACTIVE?
- **TS 38.300 §18** General (pp. 234-240)

> **Reference answer:** Yes. Small Data Transmission (SDT) allows data and signalling transmission while remaining in RRC_INACTIVE. It is enabled per radio bearer and can be initiated by the UE (MO-SDT) or the network (MT-SDT). MO-SDT requires the UL data to be below a configured amount, the DL RSRP to be above a threshold, and a valid SDT resource.

- [ ] OK

### q16: Is integrity protection mandatory for RRC signalling in NR?
- **TS 38.300 §13.1** Overview and Principles (pp. 130-132)
- **TS 33.501 §6.5.1** RRC integrity mechanisms (pp. 73-74)

> **Reference answer:** Yes. Ciphering and integrity protection are optionally configured, except for RRC signalling, for which integrity protection is always configured.

- [ ] OK

### q17: What are the main functions of the MAC sublayer?
- **TS 38.300 §6.2.1** Services and Functions (p. 57)

> **Reference answer:** MAC maps logical channels to transport channels, multiplexes and demultiplexes MAC SDUs into transport blocks, reports scheduling information, performs error correction through HARQ, and handles priorities between UEs (dynamic scheduling) and between a UE's logical channels (logical channel prioritisation).

- [ ] OK

### q18: How are UEs notified about a change in system information?
- **TS 38.300 §9.2.5** Paging (pp. 106-109)
- **TS 38.300 §7.3** Overview (pp. 68-71)

> **Reference answer:** Through Short Messages addressed with P-RNTI on PDCCH, which notify UEs in RRC_IDLE, RRC_INACTIVE and RRC_CONNECTED of system information changes and ETWS/CMAS indications. Paging messages, also addressed with P-RNTI, are sent on PCCH.

- [ ] OK

### q19: What random access preamble sequence lengths does NR support?
- **TS 38.300 §5.3.4** Random access (pp. 47-48)

> **Reference answer:** Four lengths: 839 (with 1.25 and 5 kHz subcarrier spacing), 139 (15, 30, 60, 120, 480 and 960 kHz), 571 (30, 120 and 480 kHz) and 1151 (15 and 120 kHz).

- [ ] OK

### q20: In a non-terrestrial network, what is the difference between the service link and the feeder link?
- **TS 38.300 §16.14** Overview (pp. 209-217)

> **Reference answer:** The service link is between the NTN payload (e.g. a satellite) and the UE; the feeder link is between the NTN Gateway and the NTN payload. The payload transparently forwards the radio protocol from the UE to the NTN Gateway.

- [ ] OK

### q21: What is the role of the AMF?
- **TS 23.501 §6.2.1** AMF (pp. 522-524)

> **Reference answer:** The AMF terminates the RAN control plane interface (N2) and NAS (N1), including NAS ciphering and integrity protection, and performs registration, connection, reachability and mobility management. It also supports lawful interception, transports SM messages between the UE and SMF, and handles access authentication and authorization (acting as SEAF).

- [ ] OK

### q22: Which network function allocates IP addresses to UEs?
- **TS 23.501 §6.2.2** SMF (pp. 524-526)
- **TS 23.501 §6.2.3** UPF (p. 526)

> **Reference answer:** The SMF performs UE IP address allocation and management. The address may be received from a UPF or an external data network; the UPF can allocate the UE IP address if supported, in response to an SMF request.

- [ ] OK

### q23: What does the UPF do?
- **TS 23.501 §6.2.3** UPF (p. 526)

> **Reference answer:** The UPF is the anchor point for intra- and inter-RAT mobility, the external PDU session point of interconnect to the data network, and performs packet routing and forwarding (e.g. uplink classifier, branching point), packet inspection, user plane policy enforcement, QoS handling and traffic usage reporting.

- [ ] OK

### q24: What is the Policy Control Function responsible for?
- **TS 23.501 §6.2.4** PCF (p. 527)

> **Reference answer:** The PCF supports a unified policy framework to govern network behaviour, provides policy rules to control plane functions to enforce them, and accesses subscription information relevant for policy decisions in the UDR.

- [ ] OK

### q25: Which network function generates authentication credentials and stores the SUPI?
- **TS 23.501 §6.2.7** UDM (pp. 532-533)

> **Reference answer:** The UDM. It generates 3GPP AKA authentication credentials, handles user identification (storing and managing the SUPI for each subscriber), supports SUCI de-concealment, performs subscription-based access authorization and manages the UE's serving NF registrations.

- [ ] OK

### q26: What is the AUSF responsible for?
- **TS 23.501 §6.2.8** AUSF (p. 533)

> **Reference answer:** The AUSF supports authentication for 3GPP access and untrusted non-3GPP access, and authentication of the UE for a Disaster Roaming service.

- [ ] OK

### q27: What does the NSSF determine?
- **TS 23.501 §6.2.14** NSSF (pp. 535-536)

> **Reference answer:** The NSSF selects the set of network slice instances serving the UE, determines the Allowed NSSAI and Configured NSSAI (and their mapping to Subscribed S-NSSAIs), and determines the AMF Set or a list of candidate AMFs to serve the UE.

- [ ] OK

### q28: What is the purpose of the SEPP?
- **TS 23.501 §6.2.17** SEPP (p. 536)
- **TS 33.501 §4.2.1** Security Edge Protection Proxy (SEPP) (p. 30)
- **TS 33.501 §13.1** General (pp. 171-173)

> **Reference answer:** The Security Edge Protection Proxy is a non-transparent proxy at the edge of the PLMN that protects inter-PLMN control plane messages. It performs message filtering and policing on inter-PLMN control plane interfaces, topology hiding, and enforces inter-PLMN security on the N32 interface.

- [ ] OK

### q29: What does the NWDAF do?
- **TS 23.501 §6.2.18** Network Data Analytics Function (NWDAF) (pp. 536-537)

> **Reference answer:** The NWDAF collects data from NFs, AFs, OAM and data repositories, and provides analytics information to NFs and AFs. It also supports machine learning model training and provisioning.

- [ ] OK

### q30: What is the Service Communication Proxy used for?
- **TS 23.501 §6.2.19** SCP (p. 537)

> **Reference answer:** The SCP supports indirect communication and delegated discovery between NFs, forwards and routes messages to the destination NF/NF service or the next-hop SCP, and provides communication security, load balancing, monitoring and overload control.

- [ ] OK

### q31: How does a UE on untrusted Wi-Fi connect to the 5G core?
- **TS 23.501 §6.2.9** N3IWF (pp. 533-534)
- **TS 23.501 §4.2.8.1** General Concepts to Support Trusted and Untrusted Non-3GPP Access (pp. 57-59)

> **Reference answer:** Through the N3IWF. It establishes an IPsec tunnel with the UE (IKEv2/IPsec over NWu), terminates the N2 and N3 interfaces towards the 5G core, and relays NAS (N1) signalling between the UE and the AMF.

- [ ] OK

### q32: What is a standardized 5QI?
- **TS 23.501 §5.7.4** Standardized 5QI to Qo S characteristics mapping (pp. 193-198)

> **Reference answer:** Standardized 5QI values have standardized QoS characteristics and are defined for frequently used services, so they benefit from optimized signalling. Their one-to-one mapping to QoS characteristics is in table 5.7.4-1; services without a standardized value can use dynamically assigned 5QIs.

- [ ] OK

### q33: What can a SUPI contain?
- **TS 23.501 §5.9.2** Subscription Permanent Identifier (p. 243)

> **Reference answer:** A SUPI is a globally unique identifier allocated to each subscriber and provisioned in the UDM/UDR. It may contain an IMSI, a network-specific identifier (for private networks), or a GLI or GCI together with an operator identifier.

- [ ] OK

### q34: What format must the PEI of a 3GPP UE have?
- **TS 23.501 §5.9.3** Permanent Equipment Identifier (pp. 243-244)

> **Reference answer:** If the UE supports at least one 3GPP access technology, it must be allocated a PEI in IMEI or IMEISV format. The UE presents the PEI together with an indication of the format used.

- [ ] OK

### q35: What is an always-on PDU session?
- **TS 23.501 §5.6.13** Always-on PDU session (p. 174)

> **Reference answer:** A PDU session whose user plane resources must be activated during every transition from CM-IDLE to CM-CONNECTED. The UE can request it based on an upper-layer indication, and the SMF decides whether it can be established as always-on.

- [ ] OK

### q36: What is the goal of edge computing in 5G?
- **TS 23.501 §5.13** Support for Edge Computing (pp. 251-252)

> **Reference answer:** Edge computing hosts operator and third-party services close to the UE's access point of attachment, to deliver services efficiently by reducing end-to-end latency and the load on the transport network.

- [ ] OK

### q37: Which entities can select an AMF for a UE?
- **TS 23.501 §6.3.5** AMF discovery and selection (pp. 551-554)

> **Reference answer:** The 5G-AN (e.g. RAN or N3IWF) selects an AMF for a UE. An AMF can select another AMF for relocation or when it is not appropriate to serve the UE, and other control plane NFs such as the SMF can select an AMF from the AMF set when the original AMF is unavailable.

- [ ] OK

### q38: What is the difference between SSC mode 1 and SSC mode 3?
- **TS 23.501 §5.6.9** General (pp. 167-169)

> **Reference answer:** In SSC mode 1 the PDU Session Anchor UPF is kept regardless of the access the UE uses, so IP continuity is preserved. In SSC mode 3 the network allows connectivity via a new PDU Session Anchor to the same data network before the connection to the previous anchor is released (make-before-break); it applies only to IP PDU sessions.

- [ ] OK

### q39: In SSC mode 2, what happens when the anchor UPF needs to change?
- **TS 23.501 §5.6.9** General (pp. 167-169)

> **Reference answer:** With a single PDU Session Anchor, the network may release the PDU session and instruct the UE to establish a new PDU session to the same data network immediately; a new UPF can be selected as anchor for the new session.

- [ ] OK

### q40: What makes up an S-NSSAI?
- **TS 23.501 §5.15.2** General (pp. 253-255)

> **Reference answer:** An S-NSSAI identifies a network slice and consists of a Slice/Service Type (SST), describing the expected slice behaviour, and an optional Slice Differentiator (SD) that distinguishes multiple slices of the same SST.

- [ ] OK

### q41: Which nodes do the N1, N2, N3, N4 and N6 reference points connect?
- **TS 23.501 §4.2.7** Reference points (pp. 54-57)

> **Reference answer:** N1: UE and AMF. N2: (R)AN and AMF. N3: (R)AN and UPF. N4: SMF and UPF. N6: UPF and a data network.

- [ ] OK

### q42: Why does a UE in CM-IDLE initiate the service request procedure?
- **TS 23.502 §4.2.3.2** UE Triggered Service Request (pp. 65-77)

> **Reference answer:** To send uplink signalling messages or user data, to request emergency services fallback, or in response to a network paging request. It must not do so while a Service Gap timer is running, and the AMF may perform authentication after receiving the Service Request.

- [ ] OK

### q43: What does the AN Release procedure release?
- **TS 23.502 §4.2.6** AN Release (pp. 96-99)

> **Reference answer:** It releases the logical NG-AP signalling connection between the (R)AN and the AMF with the associated N3 user plane connections, and the (R)AN signalling connection between the UE and the (R)AN with the associated (R)AN resources. All UP connections of the UE are deactivated.

- [ ] OK

### q44: How does a network function register with the NRF?
- **TS 23.502 §4.17.1** NF service Registration (pp. 552-553)
- **TS 23.501 §7.1.5** Network Function and Network Function Service registration and de- (p. 585)

> **Reference answer:** When it becomes operative for the first time, the NF instance sends an Nnrf_NFManagement_NFRegister Request with its NF profile to the NRF; the NRF stores the profile and replies with an Nnrf_NFManagement_NFRegister response.

- [ ] OK

### q45: What happens when a UE deregisters from the network?
- **TS 23.502 §4.2.2.3** General (pp. 61-64)

> **Reference answer:** The UE sends a Deregistration Request to the AMF. The AMF asks the SMF to release the UE's PDU sessions (Nsmf_PDUSession_ReleaseSMContext), the SMF releases the N4 session with the UPF, policy associations are terminated, the AMF sends a Deregistration Accept, and the signalling connection is released.

- [ ] OK

### q46: Which network functions are involved in the general registration procedure?
- **TS 23.502 §4.2.2.2** General (pp. 32-61)

> **Reference answer:** The UE sends a Registration Request via the (R)AN, which selects an AMF. The new AMF may fetch the UE context from the old AMF, selects an AUSF for authentication and security, may check the equipment identity with the EIR, selects a UDM to register and get subscription data, and selects a PCF for policy, interacting with SMFs for existing PDU sessions.

- [ ] OK

### q47: How does the UE create the SUCI?
- **TS 33.501 §6.12.2** Subscription concealed identifier (pp. 113-114)

> **Reference answer:** The SUCI contains the concealed SUPI. The UE generates it using a protection scheme with the Home Network Public Key securely provisioned by the home network; the schemes are those in Annex C or specified by the HPLMN. The scheme input is the subscription identifier part of the SUPI (the MSIN for IMSI-based SUPIs).

- [ ] OK

### q48: When does the AMF send a new 5G-GUTI to the UE?
- **TS 33.501 §6.12.3** Subscription temporary identifier (pp. 114-115)

> **Reference answer:** Only after successful activation of NAS security. The AMF shall send a new 5G-GUTI for initial registration and mobility registration update, should send one for periodic registration update, and shall send one after a Service Request sent in response to paging.

- [ ] OK

### q49: Where is the SUPI de-concealed from the SUCI, and with which key?
- **TS 33.501 §6.12.5** Subscription identifier de-concealing function (SIDF) (p. 115)
- **TS 23.501 §6.2.7** UDM (pp. 532-533)

> **Reference answer:** By the SIDF at the UDM in the home network, using the Home Network Private Key that is securely stored in the home operator's network. Only network elements of the home network may request the SIDF.

- [ ] OK

### q50: Which keys make up the 5G key hierarchy?
- **TS 33.501 §6.2** Key hierarchy (pp. 59-67)

> **Reference answer:** The long-term key K and CK/IK (or CK'/IK' for EAP-AKA'), KAUSF, KSEAF, KAMF, the NAS keys KNASint and KNASenc, KgNB and NH, the RRC keys KRRCint and KRRCenc, the UP keys KUPint and KUPenc, and KN3IWF for non-3GPP access.

- [ ] OK

### q51: How is the initial NAS message protected?
- **TS 33.501 §6.4.6** Protection of initial NAS message (pp. 72-73)

> **Reference answer:** Without a NAS security context the UE sends only the cleartext IEs needed to establish security. With a NAS security context it sends the complete initial NAS message ciphered in a NAS container along with the cleartext IEs, with the whole message integrity protected. The complete message is included in the NAS Security Mode Complete when needed.

- [ ] OK

### q52: Who decides whether user plane integrity protection is activated for a PDU session?
- **TS 33.501 §6.6.1** UP security policy (pp. 74-75)
- **TS 23.501 §5.10.3** PDU Session User Plane Security (pp. 246-249)

> **Reference answer:** The SMF provides the UP security policy for the PDU session to the gNB/ng-eNB during PDU session establishment, indicating whether UP confidentiality and/or integrity protection shall be activated for all its DRBs. The gNB/ng-eNB then activates them per DRB using RRC signalling.

- [ ] OK

### q53: What is a bidding down attack?
- **TS 33.501 §5.1.1** Mitigation of bidding down attacks (p. 31)

> **Reference answer:** An attack in which the attacker makes the UE and the network each believe the other side does not support a security feature, even though both do. 5G must ensure such attacks can be prevented.

- [ ] OK

### q54: What is the purpose of the NAS Security Mode Command procedure?
- **TS 33.501 §6.7.2** NAS security mode command procedure (pp. 78-79)

> **Reference answer:** It establishes the NAS security context between the UE and the AMF through a roundtrip: the AMF sends NAS Security Mode Command and the UE replies with NAS Security Mode Complete. It also protects the Registration Request against a man-in-the-middle attacker modifying the UE security capabilities.

- [ ] OK

### q55: Which layer provides RRC integrity protection, and is replay protection used?
- **TS 33.501 §6.5.1** RRC integrity mechanisms (pp. 73-74)

> **Reference answer:** RRC integrity protection is provided by the PDCP layer between the UE and gNB; no layer below PDCP is integrity protected. Replay protection is activated whenever integrity protection is (except with NIA0), so the receiver accepts each PDCP COUNT value only once per AS security context.

- [ ] OK

### q56: How are N32-c connections between SEPPs secured?
- **TS 33.501 §13.1** General (pp. 171-173)

> **Reference answer:** With TLS. Each SEPP keeps trust anchors (lists of trusted root certificates with their PLMN-IDs) and maps the PLMN-ID in the remote SEPP's certificate to the matching trust anchor for certificate chain verification.

- [ ] OK

### q57: Where is the Home Network Public Key stored, and can the SUPI be sent in clear text?
- **TS 33.501 §5.2.5** Subscriber privacy (pp. 33-34)

> **Reference answer:** The Home Network Public Key, its identifier and the protection scheme identifier are stored in the USIM. The SUPI should not be transferred in clear text over NG-RAN, except routing information such as MCC and MNC.

- [ ] OK

### q58: Which entity terminates NAS security and acts as the SEAF?
- **TS 23.501 §6.2.1** AMF (pp. 522-524)
- **TS 33.501 §4.3** Security entities in the 5G Core network (p. 30)

> **Reference answer:** The AMF. It terminates NAS ciphering and integrity protection and provides the Security Anchor Function (SEAF) for access authentication and authorization.

- [ ] OK

### u01: What is the best pizza in Delhi?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u02: Who won the 2022 FIFA World Cup?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u03: What is the price of an iPhone in India?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u04: What is the capital of France?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u05: Write a Python function to reverse a string.
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u06: How does Bluetooth Low Energy pairing work?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u07: Which 5G frequency bands does Airtel use in India?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u08: What peak data rate will 6G networks achieve?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u09: When will 3GPP Release 21 be frozen?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK

### u10: How much does a 5G base station cost?
*Should be unanswerable from these four specs.* Check nothing in them answers it.

- [ ] OK
