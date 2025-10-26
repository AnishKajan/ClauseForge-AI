"""
Default playbook templates for compliance analysis
"""

from typing import Dict, Any


def get_standard_contract_playbook() -> Dict[str, Any]:
    """Standard contract compliance playbook"""
    return {
        "version": "1.0",
        "name": "Standard Contract Playbook",
        "description": "Comprehensive compliance rules for standard business contracts",
        "rules": [
            {
                "id": "indemnity_clause",
                "name": "Indemnity Clause",
                "description": "Ensures proper indemnification provisions are present",
                "clause_type": "indemnity",
                "required": True,
                "patterns": [
                    "indemnify",
                    "hold harmless",
                    "defend.*against",
                    "indemnification",
                    "shall defend"
                ],
                "risk_weight": 0.9,
                "recommendations": [
                    "Add mutual indemnity clause to protect both parties",
                    "Include specific indemnification for third-party claims",
                    "Consider carve-outs for gross negligence and willful misconduct"
                ]
            },
            {
                "id": "liability_cap",
                "name": "Liability Limitation",
                "description": "Checks for liability limitation clauses",
                "clause_type": "liability",
                "required": True,
                "patterns": [
                    "liability.*limited",
                    "limitation of liability",
                    "cap.*liability",
                    "maximum liability",
                    "aggregate liability.*exceed"
                ],
                "risk_weight": 0.8,
                "recommendations": [
                    "Include reasonable liability caps to limit exposure",
                    "Consider mutual liability limitations",
                    "Exclude certain damages from liability caps (e.g., IP infringement)"
                ]
            },
            {
                "id": "termination_clause",
                "name": "Termination Rights",
                "description": "Ensures proper termination provisions",
                "clause_type": "termination",
                "required": True,
                "patterns": [
                    "terminate.*agreement",
                    "termination.*notice",
                    "end.*agreement",
                    "terminate.*cause",
                    "terminate.*convenience"
                ],
                "risk_weight": 0.7,
                "recommendations": [
                    "Include termination for cause provisions",
                    "Add termination for convenience with appropriate notice",
                    "Specify post-termination obligations and data handling"
                ]
            },
            {
                "id": "confidentiality_clause",
                "name": "Confidentiality Provisions",
                "description": "Checks for confidentiality and non-disclosure terms",
                "clause_type": "confidentiality",
                "required": True,
                "patterns": [
                    "confidential",
                    "non-disclosure",
                    "proprietary information",
                    "trade secrets",
                    "confidentiality"
                ],
                "risk_weight": 0.6,
                "recommendations": [
                    "Include mutual confidentiality obligations",
                    "Define what constitutes confidential information",
                    "Specify exceptions to confidentiality obligations"
                ]
            },
            {
                "id": "governing_law",
                "name": "Governing Law",
                "description": "Ensures governing law and jurisdiction clauses",
                "clause_type": "governing_law",
                "required": True,
                "patterns": [
                    "governed by.*law",
                    "governing law",
                    "jurisdiction",
                    "courts of",
                    "applicable law"
                ],
                "risk_weight": 0.5,
                "recommendations": [
                    "Specify clear governing law and jurisdiction",
                    "Consider neutral jurisdiction for international contracts",
                    "Include dispute resolution mechanisms"
                ]
            },
            {
                "id": "force_majeure",
                "name": "Force Majeure",
                "description": "Checks for force majeure provisions",
                "clause_type": "force_majeure",
                "required": False,
                "patterns": [
                    "force majeure",
                    "act of god",
                    "unforeseeable circumstances",
                    "beyond.*control",
                    "natural disaster"
                ],
                "risk_weight": 0.3,
                "recommendations": [
                    "Consider adding force majeure clause for unforeseeable events",
                    "Include pandemic and cyber security incidents",
                    "Specify notice requirements and mitigation obligations"
                ]
            },
            {
                "id": "intellectual_property",
                "name": "Intellectual Property Rights",
                "description": "Ensures IP ownership and licensing terms",
                "clause_type": "intellectual_property",
                "required": True,
                "patterns": [
                    "intellectual property",
                    "copyright",
                    "trademark",
                    "patent",
                    "proprietary rights",
                    "work for hire"
                ],
                "risk_weight": 0.8,
                "recommendations": [
                    "Clearly define IP ownership and licensing rights",
                    "Include IP indemnification provisions",
                    "Address pre-existing IP and derivative works"
                ]
            },
            {
                "id": "payment_terms",
                "name": "Payment Terms",
                "description": "Checks for clear payment obligations",
                "clause_type": "payment",
                "required": True,
                "patterns": [
                    "payment.*due",
                    "invoice",
                    "payment terms",
                    "net.*days",
                    "late fees",
                    "interest.*overdue"
                ],
                "risk_weight": 0.6,
                "recommendations": [
                    "Include clear payment terms and due dates",
                    "Add late payment penalties and interest",
                    "Specify acceptable payment methods"
                ]
            }
        ]
    }


def get_employment_contract_playbook() -> Dict[str, Any]:
    """Employment contract compliance playbook"""
    return {
        "version": "1.0",
        "name": "Employment Contract Playbook",
        "description": "Compliance rules for employment agreements",
        "rules": [
            {
                "id": "at_will_employment",
                "name": "At-Will Employment",
                "description": "Checks for at-will employment provisions",
                "clause_type": "employment_terms",
                "required": True,
                "patterns": [
                    "at-will",
                    "at will",
                    "terminate.*without cause",
                    "employment.*will"
                ],
                "risk_weight": 0.7,
                "recommendations": [
                    "Include clear at-will employment language",
                    "Specify notice requirements for termination",
                    "Consider probationary period provisions"
                ]
            },
            {
                "id": "non_compete",
                "name": "Non-Compete Agreement",
                "description": "Checks for non-compete restrictions",
                "clause_type": "restrictive_covenant",
                "required": False,
                "patterns": [
                    "non-compete",
                    "not compete",
                    "restraint.*trade",
                    "competitive.*business"
                ],
                "risk_weight": 0.8,
                "recommendations": [
                    "Ensure non-compete restrictions are reasonable in scope and duration",
                    "Consider state law limitations on non-compete agreements",
                    "Include consideration for non-compete restrictions"
                ]
            },
            {
                "id": "confidentiality_employment",
                "name": "Employee Confidentiality",
                "description": "Ensures confidentiality obligations for employees",
                "clause_type": "confidentiality",
                "required": True,
                "patterns": [
                    "confidential",
                    "proprietary information",
                    "trade secrets",
                    "non-disclosure"
                ],
                "risk_weight": 0.9,
                "recommendations": [
                    "Include comprehensive confidentiality provisions",
                    "Define scope of confidential information",
                    "Specify post-employment confidentiality obligations"
                ]
            }
        ]
    }


def get_vendor_agreement_playbook() -> Dict[str, Any]:
    """Vendor/supplier agreement compliance playbook"""
    return {
        "version": "1.0",
        "name": "Vendor Agreement Playbook",
        "description": "Compliance rules for vendor and supplier agreements",
        "rules": [
            {
                "id": "service_level_agreement",
                "name": "Service Level Agreement",
                "description": "Checks for SLA and performance standards",
                "clause_type": "performance",
                "required": True,
                "patterns": [
                    "service level",
                    "SLA",
                    "performance standards",
                    "uptime",
                    "availability.*percent"
                ],
                "risk_weight": 0.8,
                "recommendations": [
                    "Include specific service level requirements",
                    "Add penalties for SLA breaches",
                    "Define measurement and reporting procedures"
                ]
            },
            {
                "id": "data_security",
                "name": "Data Security Requirements",
                "description": "Ensures data protection and security provisions",
                "clause_type": "data_security",
                "required": True,
                "patterns": [
                    "data security",
                    "cybersecurity",
                    "data protection",
                    "GDPR",
                    "privacy",
                    "encryption"
                ],
                "risk_weight": 0.9,
                "recommendations": [
                    "Include comprehensive data security requirements",
                    "Specify compliance with applicable privacy laws",
                    "Add data breach notification procedures"
                ]
            },
            {
                "id": "insurance_requirements",
                "name": "Insurance Requirements",
                "description": "Checks for adequate insurance coverage",
                "clause_type": "insurance",
                "required": True,
                "patterns": [
                    "insurance",
                    "coverage",
                    "liability insurance",
                    "errors and omissions",
                    "professional liability"
                ],
                "risk_weight": 0.7,
                "recommendations": [
                    "Require adequate insurance coverage levels",
                    "Include additional insured provisions",
                    "Specify insurance certificate requirements"
                ]
            }
        ]
    }


def get_saas_agreement_playbook() -> Dict[str, Any]:
    """SaaS agreement compliance playbook"""
    return {
        "version": "1.0",
        "name": "SaaS Agreement Playbook",
        "description": "Compliance rules for Software as a Service agreements",
        "rules": [
            {
                "id": "data_ownership",
                "name": "Data Ownership",
                "description": "Ensures clear data ownership provisions",
                "clause_type": "data_rights",
                "required": True,
                "patterns": [
                    "data ownership",
                    "customer data",
                    "data rights",
                    "data portability",
                    "data export"
                ],
                "risk_weight": 0.9,
                "recommendations": [
                    "Clearly establish customer data ownership",
                    "Include data portability and export rights",
                    "Specify data deletion procedures upon termination"
                ]
            },
            {
                "id": "uptime_guarantee",
                "name": "Uptime Guarantee",
                "description": "Checks for service availability guarantees",
                "clause_type": "availability",
                "required": True,
                "patterns": [
                    "uptime",
                    "availability",
                    "service level",
                    "99\\.9",
                    "downtime"
                ],
                "risk_weight": 0.8,
                "recommendations": [
                    "Include specific uptime guarantees",
                    "Add service credits for downtime",
                    "Define planned vs. unplanned maintenance"
                ]
            },
            {
                "id": "security_compliance",
                "name": "Security Compliance",
                "description": "Ensures security and compliance certifications",
                "clause_type": "security",
                "required": True,
                "patterns": [
                    "SOC 2",
                    "ISO 27001",
                    "security certification",
                    "compliance audit",
                    "penetration test"
                ],
                "risk_weight": 0.9,
                "recommendations": [
                    "Require relevant security certifications",
                    "Include regular security assessments",
                    "Specify incident response procedures"
                ]
            }
        ]
    }


def get_playbook_by_type(playbook_type: str) -> Dict[str, Any]:
    """Get playbook template by type"""
    playbooks = {
        "standard": get_standard_contract_playbook,
        "employment": get_employment_contract_playbook,
        "vendor": get_vendor_agreement_playbook,
        "saas": get_saas_agreement_playbook
    }
    
    if playbook_type not in playbooks:
        raise ValueError(f"Unknown playbook type: {playbook_type}")
    
    return playbooks[playbook_type]()


def get_available_playbook_types() -> list[str]:
    """Get list of available playbook types"""
    return ["standard", "employment", "vendor", "saas"]