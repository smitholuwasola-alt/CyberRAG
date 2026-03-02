# CyberRAG: Cybersecurity Education with Knowledge Graphs

CyberRAG is a question-answering system designed to help students study cybersecurity. It uses a structured database of cybersecurity knowledge to answer questions in a way that is traceable and grounded in facts, rather than relying on a general-purpose AI that might guess or make things up.

The system was built and tested using the AISecKG dataset, which is a collection of cybersecurity concepts, tools, and relationships extracted from real university lab documents.

---

## What Problem Does This Solve?

Cybersecurity is a large and technical field. Students preparing for certifications like CISSP need to understand hundreds of concepts and how they relate to each other. Most study tools either give you raw text to read or use general AI chatbots that can produce wrong answers on specialized topics.

CyberRAG takes a different approach. It organizes cybersecurity knowledge into a structured map of facts, then uses that map to answer questions with supporting evidence. Every answer the system gives points back to the specific facts it used to reach that conclusion.

---

## What Is in This Repository?

The repository contains three main things.

The first is the knowledge dataset. This is a set of spreadsheet files listing 963 cybersecurity entities such as tools, attack types, and concepts, along with 728 relationships between them. For example, the dataset records that Snort uses Intrusion Detection, that Snort can detect network attacks, and that a packet logger is part of Snort.

The second is the source documents. These are six cybersecurity lab documents that the dataset was built from. They cover topics including Nmap network scanning, Snort intrusion detection, firewall penetration testing, and general system security. The documents are included in both their original Word format and as plain text files.

The third is the code. This includes scripts to build the knowledge graph from the spreadsheet files, a query engine that answers questions by searching the graph, a pipeline that ties everything together, and a script that answers CISSP-style multiple choice questions automatically.

---

## How Does It Work?

When you ask the system a question, it goes through the following steps.

First, it reads the question and identifies any cybersecurity terms it recognizes, such as tool names or attack types. Second, it searches the knowledge graph for those terms and finds everything connected to them. Third, it collects the relevant facts and combines them into an answer. Fourth, if the question is multiple choice, it scores each option against the facts it found and picks the best match.

For example, given the question "What is Snort used for?", the system would find the Snort entity in the graph, retrieve facts like "Snort uses Intrusion Detection" and "Snort can detect network attacks", and use those facts to select the correct answer.

---

## What Is the Dataset?

The dataset was created by reading six university cybersecurity lab documents and manually labeling the important concepts and how they connect. The topics covered are Nmap network scanning, penetration testing with firewall and IDS evasion, system security fundamentals, advanced system security, and network security tools.

From these documents, the team identified 963 unique cybersecurity entities across categories including tools, attacks, data types, functions, and system components. They also defined 9 types of relationships such as uses, is a part of, can detect, can harm, and can exploit. These entities and relationships were recorded as 728 individual facts called triples, each in the format of subject, relationship, object.

The dataset also includes annotated training data for building machine learning models that can automatically read new cybersecurity documents and extract entities from them, which would allow the knowledge base to grow over time.

---

## Who Is This For?

Students studying for the CISSP certification or other cybersecurity credentials can use CyberRAG as a study tool that answers questions with referenced facts rather than guesses.

Instructors at universities can use the dataset and source documents as a foundation for building AI-assisted course materials.

Security trainers in organizations can deploy the system to provide employees with a reliable, domain-specific assistant for learning security concepts.

Researchers in AI, natural language processing, or cybersecurity can use the dataset to build better knowledge graphs, train named entity recognition models, or test new question-answering approaches.

---

## How to Get Started

Install the required Python libraries by running the following command.

```
pip install pandas networkx nltk numpy
```

To build the knowledge graph from the dataset files, run the kg_builder.py script. To answer questions using the graph, run the answer_cissp_questions.py script with a file containing your questions. To run the complete pipeline from start to finish, use main_pipeline.py.

---

## Limitations

The system only knows what is in the six source lab documents. Questions about cybersecurity topics not covered in those documents may not get a useful answer.

The way the system finds relevant entities is based on matching keywords, so if a question uses different wording than the dataset, the system may miss the connection.

The system does not reason across multiple steps the way a human expert would. It retrieves facts directly connected to the entities in the question, but cannot chain together several reasoning steps to reach a deeper conclusion.

---

## Future Plans

The team plans to improve entity matching so it understands related words and synonyms, not just exact keyword matches. They also plan to expand the knowledge base by pulling in information from sources like the MITRE ATT&CK framework and NIST security guidelines. Additionally, they aim to integrate a neural reading model on top of the graph retrieval to improve answer accuracy on harder questions.
