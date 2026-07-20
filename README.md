# Side-Channel Information Leakage on Black-Box Evaluation Platforms

## 📌 Abstract

This repository demonstrates a **Side-Channel Attack (SCA)** Proof of Concept (PoC) targeting automated programming evaluation systems (Online Judge platforms). 
The research explores how subtle feedback metrics—specifically `memory_cost` and error states—can be weaponized to establish a high-bandwidth covert channel, potentially exfiltrating black-box test cases without direct file access.

## 🔬 Core Research & Contribution

1. **Covert Channel Optimization:** Extended the leakage bandwidth from 1-bit (Runtime Error classification) to 9-bits per execution by applying **Linear Regression** to map precise hardware memory allocation variations.
2. **Deterministic Data Reconstruction:** Designed an algorithmic approach utilizing **Lexicographical Ordering** and **Longest Common Prefix (LCP)** to isolate and reconstruct individual data streams from a unified multi-threaded maximum-value filter.
3. **Anti-Compiler Optimization:** Developed memory boundary traversal techniques to counter Dead Code Elimination (DCE) by modern compilers, ensuring stable hardware state side-channels.

## 🛑 Academic Disclaimer & Ethical Notice

- **Educational Purpose Only:** This project is strictly for cybersecurity research and educational purposes regarding software side-channel mitigations.
- **No Live Targeting:** All hardcoded infrastructure dependencies have been removed. The PoC is configured to run only against a localized sandbox dummy server (`localhost`).
- **Mitigation Proposed:** To prevent this vulnerability, platform administrators should inject differential privacy noise into returned resource cost metrics (e.g., fuzzing the `memory_cost` response values) or restrict identical submission frequencies per user.
