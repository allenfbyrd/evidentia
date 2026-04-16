"""Generate MITRE threat catalogs + CISA KEV — Tier B.

MITRE ATT&CK, CWE, and CAPEC are free-to-use under MITRE's terms
(essentially public-domain-like with attribution). CISA KEV is a US
federal government publication (public domain).

v0.2.0 ships a representative sample — the refresh CI workflow in M5
will pull fresh data from upstream on a daily schedule.
"""

from __future__ import annotations

from _generators import (  # type: ignore[import-not-found]
    emit_technique_catalog,
    emit_vulnerability_catalog,
)

ATTACK_URL = "https://attack.mitre.org"


# ---------------------------------------------------------------------------
# MITRE ATT&CK Enterprise — representative sample of high-use techniques
# ---------------------------------------------------------------------------

ATTACK_TACTICS = [
    "Reconnaissance", "Resource Development", "Initial Access", "Execution",
    "Persistence", "Privilege Escalation", "Defense Evasion",
    "Credential Access", "Discovery", "Lateral Movement", "Collection",
    "Command and Control", "Exfiltration", "Impact",
]

ATTACK_TECHNIQUES = [
    ("T1078", "Valid Accounts", "Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"], False, None),
    ("T1078.001", "Default Accounts", "Adversaries may obtain and abuse credentials of a default account as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"], True, "T1078"),
    ("T1078.002", "Domain Accounts", "Adversaries may obtain and abuse credentials of a domain account as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"], True, "T1078"),
    ("T1078.003", "Local Accounts", "Adversaries may obtain and abuse credentials of a local account as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"], True, "T1078"),
    ("T1078.004", "Cloud Accounts", "Valid accounts in cloud environments may allow adversaries to perform actions to achieve Initial Access, Persistence, Privilege Escalation, or Defense Evasion.", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"], True, "T1078"),
    ("T1566", "Phishing", "Adversaries may send phishing messages to gain access to victim systems.", ["Initial Access"], False, None),
    ("T1566.001", "Spearphishing Attachment", "Adversaries may send spearphishing emails with a malicious attachment in an attempt to gain access to victim systems.", ["Initial Access"], True, "T1566"),
    ("T1566.002", "Spearphishing Link", "Adversaries may send spearphishing emails with a malicious link in an attempt to gain access to victim systems.", ["Initial Access"], True, "T1566"),
    ("T1190", "Exploit Public-Facing Application", "Adversaries may attempt to exploit a weakness in an Internet-facing host or system to initially access a network.", ["Initial Access"], False, None),
    ("T1133", "External Remote Services", "Adversaries may leverage external-facing remote services to initially access and/or persist within a network.", ["Initial Access", "Persistence"], False, None),
    ("T1059", "Command and Scripting Interpreter", "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.", ["Execution"], False, None),
    ("T1059.001", "PowerShell", "Adversaries may abuse PowerShell commands and scripts for execution.", ["Execution"], True, "T1059"),
    ("T1059.003", "Windows Command Shell", "Adversaries may abuse the Windows command shell for execution.", ["Execution"], True, "T1059"),
    ("T1204", "User Execution", "An adversary may rely upon specific actions by a user in order to gain execution.", ["Execution"], False, None),
    ("T1053", "Scheduled Task/Job", "Adversaries may abuse task scheduling functionality to facilitate initial or recurring execution of malicious code.", ["Execution", "Persistence", "Privilege Escalation"], False, None),
    ("T1547", "Boot or Logon Autostart Execution", "Adversaries may configure system settings to automatically execute a program during system boot or logon.", ["Persistence", "Privilege Escalation"], False, None),
    ("T1068", "Exploitation for Privilege Escalation", "Adversaries may exploit software vulnerabilities in an attempt to elevate privileges.", ["Privilege Escalation"], False, None),
    ("T1134", "Access Token Manipulation", "Adversaries may modify access tokens to operate under a different user or system security context.", ["Defense Evasion", "Privilege Escalation"], False, None),
    ("T1562", "Impair Defenses", "Adversaries may maliciously modify components of a victim environment in order to hinder or disable defensive mechanisms.", ["Defense Evasion"], False, None),
    ("T1562.001", "Disable or Modify Tools", "Adversaries may modify and/or disable security tools to avoid possible detection of their malware/tools and activities.", ["Defense Evasion"], True, "T1562"),
    ("T1027", "Obfuscated Files or Information", "Adversaries may attempt to make an executable or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents.", ["Defense Evasion"], False, None),
    ("T1003", "OS Credential Dumping", "Adversaries may attempt to dump credentials to obtain account login and credential material.", ["Credential Access"], False, None),
    ("T1003.001", "LSASS Memory", "Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS).", ["Credential Access"], True, "T1003"),
    ("T1110", "Brute Force", "Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.", ["Credential Access"], False, None),
    ("T1552", "Unsecured Credentials", "Adversaries may search compromised systems to find and obtain insecurely stored credentials.", ["Credential Access"], False, None),
    ("T1082", "System Information Discovery", "An adversary may attempt to get detailed information about the operating system and hardware.", ["Discovery"], False, None),
    ("T1083", "File and Directory Discovery", "Adversaries may enumerate files and directories or may search in specific locations of a host or network share for certain information.", ["Discovery"], False, None),
    ("T1018", "Remote System Discovery", "Adversaries may attempt to get a listing of other systems by IP address, hostname, or other logical identifier on a network.", ["Discovery"], False, None),
    ("T1021", "Remote Services", "Adversaries may use valid accounts to log into a service that accepts remote connections.", ["Lateral Movement"], False, None),
    ("T1021.001", "Remote Desktop Protocol", "Adversaries may use Valid Accounts to log into a computer using the Remote Desktop Protocol (RDP).", ["Lateral Movement"], True, "T1021"),
    ("T1005", "Data from Local System", "Adversaries may search local system sources to find files of interest and sensitive data prior to Exfiltration.", ["Collection"], False, None),
    ("T1560", "Archive Collected Data", "An adversary may compress and/or encrypt data that is collected prior to exfiltration.", ["Collection"], False, None),
    ("T1071", "Application Layer Protocol", "Adversaries may communicate using OSI application layer protocols to avoid detection/network filtering by blending in with existing traffic.", ["Command and Control"], False, None),
    ("T1071.001", "Web Protocols", "Adversaries may communicate using application layer protocols associated with web traffic (HTTP/HTTPS) to avoid detection.", ["Command and Control"], True, "T1071"),
    ("T1105", "Ingress Tool Transfer", "Adversaries may transfer tools or other files from an external system into a compromised environment.", ["Command and Control"], False, None),
    ("T1041", "Exfiltration Over C2 Channel", "Adversaries may steal data by exfiltrating it over an existing command and control channel.", ["Exfiltration"], False, None),
    ("T1567", "Exfiltration Over Web Service", "Adversaries may use an existing, legitimate external Web service to exfiltrate data rather than their primary command and control channel.", ["Exfiltration"], False, None),
    ("T1486", "Data Encrypted for Impact", "Adversaries may encrypt data on target systems or on large numbers of systems in a network to interrupt availability to system and network resources.", ["Impact"], False, None),
    ("T1490", "Inhibit System Recovery", "Adversaries may delete or remove built-in data and turn off services designed to aid in the recovery of a corrupted system to prevent recovery.", ["Impact"], False, None),
    ("T1489", "Service Stop", "Adversaries may stop or disable services on a system to render those services unavailable to legitimate users.", ["Impact"], False, None),
    ("T1485", "Data Destruction", "Adversaries may destroy data and files on specific systems or in large numbers on a network to interrupt availability to systems, services, and network resources.", ["Impact"], False, None),
]

emit_technique_catalog(
    framework_id="mitre-attack-enterprise",
    framework_name="MITRE ATT&CK Enterprise",
    version="v15.1 (2024)",
    source="MITRE Corporation — https://attack.mitre.org (free to use with attribution)",
    tactics=ATTACK_TACTICS,
    techniques=[
        {
            "id": tid,
            "name": name,
            "description": desc,
            "tactic_names": tactics,
            "is_subtechnique": is_sub,
            "parent_technique_id": parent,
            "platforms": ["Windows", "Linux", "macOS"] if not is_sub else [],
        }
        for tid, name, desc, tactics, is_sub, parent in ATTACK_TECHNIQUES
    ],
    tier="B",
    license_terms="© MITRE Corporation. ATT&CK is freely available under MITRE's terms of use.",
)


# ---------------------------------------------------------------------------
# MITRE CWE (Common Weakness Enumeration) — top 25 sample
# ---------------------------------------------------------------------------

CWE_TOP_25_2024 = [
    ("CWE-79", "Cross-site Scripting", "Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')"),
    ("CWE-787", "Out-of-bounds Write", "The product writes data past the end, or before the beginning, of the intended buffer."),
    ("CWE-89", "SQL Injection", "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')"),
    ("CWE-352", "Cross-Site Request Forgery (CSRF)", "The web application does not verify that a valid request from the user was intentionally provided."),
    ("CWE-22", "Path Traversal", "Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"),
    ("CWE-125", "Out-of-bounds Read", "The product reads data past the end, or before the beginning, of the intended buffer."),
    ("CWE-78", "OS Command Injection", "Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"),
    ("CWE-416", "Use After Free", "Referencing memory after it has been freed can cause a program to crash, use unexpected values, or execute code."),
    ("CWE-862", "Missing Authorization", "The product does not perform an authorization check when an actor attempts to access a resource or perform an action."),
    ("CWE-434", "Unrestricted Upload of File with Dangerous Type", "The product allows the attacker to upload or transfer files of dangerous types."),
    ("CWE-94", "Code Injection", "Improper Control of Generation of Code ('Code Injection')"),
    ("CWE-20", "Improper Input Validation", "The product receives input or data, but it does not validate or incorrectly validates that the input has the properties that are required to process the data safely."),
    ("CWE-77", "Command Injection", "Improper Neutralization of Special Elements used in a Command ('Command Injection')"),
    ("CWE-287", "Improper Authentication", "When an actor claims to have a given identity, the product does not prove or insufficiently proves that the claim is correct."),
    ("CWE-269", "Improper Privilege Management", "The product does not properly assign, modify, track, or check privileges for an actor, creating an unintended sphere of control."),
    ("CWE-502", "Deserialization of Untrusted Data", "The product deserializes untrusted data without sufficiently verifying that the resulting data will be valid."),
    ("CWE-200", "Exposure of Sensitive Information to an Unauthorized Actor", "The product exposes sensitive information to an actor that is not explicitly authorized to have access to that information."),
    ("CWE-863", "Incorrect Authorization", "The product performs an authorization check when an actor attempts to access a resource or perform an action, but it does not correctly perform the check."),
    ("CWE-918", "Server-Side Request Forgery (SSRF)", "The web server receives a URL or similar request from an upstream component and retrieves the contents of this URL, but does not sufficiently ensure that the request is being sent to the expected destination."),
    ("CWE-119", "Improper Restriction of Operations within the Bounds of a Memory Buffer", "The product performs operations on a memory buffer, but it can read from or write to a memory location that is outside of the intended boundary of the buffer."),
    ("CWE-476", "NULL Pointer Dereference", "A NULL pointer dereference occurs when the application dereferences a pointer that it expects to be valid, but is NULL, typically causing a crash or exit."),
    ("CWE-798", "Use of Hard-coded Credentials", "The product contains hard-coded credentials, such as a password or cryptographic key, which it uses for its own inbound authentication, outbound communication to external components, or encryption of internal data."),
    ("CWE-190", "Integer Overflow or Wraparound", "The product performs a calculation that can produce an integer overflow or wraparound when the logic assumes that the resulting value will always be larger than the original value."),
    ("CWE-400", "Uncontrolled Resource Consumption", "The product does not properly control the allocation and maintenance of a limited resource, thereby enabling an actor to influence the amount of resources consumed, eventually leading to the exhaustion of available resources."),
    ("CWE-306", "Missing Authentication for Critical Function", "The product does not perform any authentication for functionality that requires a provable user identity or consumes a significant amount of resources."),
]

emit_technique_catalog(
    framework_id="mitre-cwe",
    framework_name="MITRE Common Weakness Enumeration (CWE) — 2024 Top 25 Sample",
    version="4.14 (2024)",
    source="MITRE Corporation — https://cwe.mitre.org (free to use)",
    techniques=[
        {
            "id": cwe_id,
            "name": name,
            "description": desc,
            "tactic_names": ["Software Weakness"],
            "is_subtechnique": False,
        }
        for cwe_id, name, desc in CWE_TOP_25_2024
    ],
    tier="B",
    license_terms="© MITRE Corporation. CWE is freely available.",
)


# ---------------------------------------------------------------------------
# MITRE CAPEC — sample
# ---------------------------------------------------------------------------

CAPEC_SAMPLE = [
    ("CAPEC-21", "Exploitation of Trusted Identifiers", "An attacker guesses the identifiers used to access resources."),
    ("CAPEC-66", "SQL Injection", "Inject SQL commands in entry points."),
    ("CAPEC-70", "Try Common or Default Usernames and Passwords", "Brute force with common credential lists."),
    ("CAPEC-98", "Phishing", "Send deceptive communications to obtain sensitive information."),
    ("CAPEC-148", "Content Spoofing", "Modify content to deceive users."),
    ("CAPEC-232", "Exploitation of Privilege/Trust", "Gain privileged access through trust relationships."),
    ("CAPEC-242", "Code Injection", "Inject code into a target environment."),
    ("CAPEC-248", "Command Injection", "Inject commands into application input."),
    ("CAPEC-509", "Kerberoasting", "Request service tickets and crack them offline."),
    ("CAPEC-560", "Use of Known Domain Credentials", "Reuse domain credentials across systems."),
]

emit_technique_catalog(
    framework_id="mitre-capec",
    framework_name="MITRE Common Attack Pattern Enumeration and Classification (CAPEC) — Sample",
    version="v3.9 (2024)",
    source="MITRE Corporation — https://capec.mitre.org (free to use)",
    techniques=[
        {
            "id": cid,
            "name": name,
            "description": desc,
            "tactic_names": ["Attack Pattern"],
            "is_subtechnique": False,
        }
        for cid, name, desc in CAPEC_SAMPLE
    ],
    tier="B",
    license_terms="© MITRE Corporation. CAPEC is freely available.",
)


# ---------------------------------------------------------------------------
# CISA KEV — Known Exploited Vulnerabilities (sample of most-notable)
# ---------------------------------------------------------------------------

KEV_SAMPLE = [
    {
        "cve_id": "CVE-2021-44228",
        "vendor": "Apache Software Foundation",
        "product": "Log4j2",
        "vulnerability_name": "Apache Log4j2 Remote Code Execution (Log4Shell)",
        "description": "Apache Log4j2 JNDI features do not protect against attacker controlled LDAP and other JNDI related endpoints. An attacker who can control log messages or log message parameters can execute arbitrary code loaded from LDAP servers.",
        "cwe_ids": ["CWE-20", "CWE-400", "CWE-502"],
        "date_added": "2021-12-10",
        "known_ransomware_use": True,
        "required_action": "Apply vendor updates; enable log4j2.formatMsgNoLookups=true or remove JndiLookup class.",
        "cvss_v3_score": 10.0,
        "due_date": "2021-12-24",
    },
    {
        "cve_id": "CVE-2023-34362",
        "vendor": "Progress Software",
        "product": "MOVEit Transfer",
        "vulnerability_name": "Progress MOVEit Transfer SQL Injection",
        "description": "Progress MOVEit Transfer contains a SQL injection vulnerability that could allow an unauthenticated attacker to access the MOVEit database.",
        "cwe_ids": ["CWE-89"],
        "date_added": "2023-06-02",
        "known_ransomware_use": True,
        "required_action": "Apply vendor patches.",
        "cvss_v3_score": 9.8,
        "due_date": "2023-06-23",
    },
    {
        "cve_id": "CVE-2024-21887",
        "vendor": "Ivanti",
        "product": "Connect Secure and Policy Secure",
        "vulnerability_name": "Ivanti Connect Secure and Policy Secure Command Injection",
        "description": "A command injection vulnerability in web components of Ivanti Connect Secure and Ivanti Policy Secure allows an authenticated administrator to send specially crafted requests and execute arbitrary commands on the appliance.",
        "cwe_ids": ["CWE-77"],
        "date_added": "2024-01-10",
        "known_ransomware_use": False,
        "required_action": "Apply mitigations per vendor instructions; apply updates when available.",
        "cvss_v3_score": 9.1,
        "due_date": "2024-01-22",
    },
    {
        "cve_id": "CVE-2017-0144",
        "vendor": "Microsoft",
        "product": "SMBv1 Server",
        "vulnerability_name": "Microsoft SMBv1 Remote Code Execution (EternalBlue)",
        "description": "The SMBv1 server in Microsoft Windows allows remote attackers to execute arbitrary code via crafted packets.",
        "cwe_ids": ["CWE-20"],
        "date_added": "2022-03-25",
        "known_ransomware_use": True,
        "required_action": "Apply MS17-010; disable SMBv1.",
        "cvss_v3_score": 8.8,
        "due_date": "2022-04-15",
    },
    {
        "cve_id": "CVE-2019-19781",
        "vendor": "Citrix",
        "product": "ADC and Gateway",
        "vulnerability_name": "Citrix ADC and Gateway Directory Traversal",
        "description": "Directory traversal vulnerability in Citrix ADC and Citrix Gateway allows unauthenticated remote code execution.",
        "cwe_ids": ["CWE-22"],
        "date_added": "2021-11-03",
        "known_ransomware_use": True,
        "required_action": "Apply Citrix security bulletin CTX267027.",
        "cvss_v3_score": 9.8,
        "due_date": "2021-11-17",
    },
    {
        "cve_id": "CVE-2023-23397",
        "vendor": "Microsoft",
        "product": "Outlook",
        "vulnerability_name": "Microsoft Outlook Privilege Escalation",
        "description": "An NTLM relay vulnerability in Microsoft Outlook that allows attackers to steal credentials and gain elevated privileges.",
        "cwe_ids": ["CWE-294"],
        "date_added": "2023-03-14",
        "known_ransomware_use": True,
        "required_action": "Apply Microsoft patches.",
        "cvss_v3_score": 9.8,
        "due_date": "2023-04-04",
    },
    {
        "cve_id": "CVE-2022-26134",
        "vendor": "Atlassian",
        "product": "Confluence Server and Data Center",
        "vulnerability_name": "Atlassian Confluence Server and Data Center OGNL Injection",
        "description": "An unauthenticated, remote attacker could execute arbitrary code on Confluence Server or Data Center.",
        "cwe_ids": ["CWE-94"],
        "date_added": "2022-06-02",
        "known_ransomware_use": True,
        "required_action": "Apply Atlassian patches or take servers offline.",
        "cvss_v3_score": 9.8,
        "due_date": "2022-06-06",
    },
    {
        "cve_id": "CVE-2024-3400",
        "vendor": "Palo Alto Networks",
        "product": "PAN-OS",
        "vulnerability_name": "Palo Alto Networks PAN-OS Command Injection",
        "description": "A command injection vulnerability in the GlobalProtect feature of PAN-OS software for specific versions with specific feature configurations may allow an unauthenticated attacker to execute arbitrary code with root privileges on the firewall.",
        "cwe_ids": ["CWE-77"],
        "date_added": "2024-04-12",
        "known_ransomware_use": False,
        "required_action": "Apply vendor hotfixes.",
        "cvss_v3_score": 10.0,
        "due_date": "2024-04-19",
    },
]

emit_vulnerability_catalog(
    framework_id="cisa-kev",
    framework_name="CISA Known Exploited Vulnerabilities (sample)",
    version="Continuously updated (sample as of early 2026)",
    source="CISA — https://www.cisa.gov/known-exploited-vulnerabilities-catalog (U.S. Government work)",
    vulnerabilities=KEV_SAMPLE,
    tier="B",
    license_terms="U.S. Government work, public domain. Sample bundled in ControlBridge; refresh CI pulls the full KEV daily.",
)


if __name__ == "__main__":
    print("Generated MITRE threat catalogs + CISA KEV sample.")
