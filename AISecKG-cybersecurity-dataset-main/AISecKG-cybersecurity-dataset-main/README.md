#CyberRAG: Cybersecurity Education with Knowledge Graphs
CyberRAG is a question-answering system designed to help students study cybersecurity. It uses a structured database of cybersecurity knowledge to answer questions in a way that is traceable and grounded in facts, rather than relying on a general-purpose AI that might guess or make things up.

The system was built and tested using the AISecKG dataset, which is a collection of cybersecurity concepts, tools, and relationships extracted from real university lab documents.

What Problem Does This Solve?
Cybersecurity is a large and technical field. Students preparing for certifications like CISSP need to understand hundreds of concepts and how they relate to each other. Most study tools either give you raw text to read or use general AI chatbots that can produce wrong answers on specialized topics.

CyberRAG takes a different approach. It organizes cybersecurity knowledge into a structured map of facts, then uses that map to answer questions with supporting evidence. Every answer the system gives points back to the specific facts it used to reach that conclusion.

What Is in This Repository?
The repository contains three main things.

The first is the knowledge dataset. This is a set of spreadsheet files listing 963 cybersecurity entities such as tools, attack types, and concepts, along with 728 relationships between them. For example, the dataset records that Snort uses Intrusion Detection, that Snort can detect network attacks, and that a packet logger is part of Snort.

The second is the source documents. These are six cybersecurity lab documents that the dataset was built from. They cover topics including Nmap network scanning, Snort intrusion detection, firewall penetration testing, and general system security. The documents are included in both their original Word format and as plain text files.

The third is the code. This includes scripts to build the knowledge graph from the spreadsheet files, a query engine that answers questions by searching the graph, a pipeline that ties everything together, and a script that answers CISSP-style multiple choice questions automatically.

How Does It Work?
When you ask the system a question, it goes through the following steps.

First, it reads the question and identifies any cybersecurity terms it recognizes, such as tool names or attack types. Second, it searches the knowledge graph for those terms and finds everything connected to them. Third, it collects the relevant facts and combines them into an answer. Fourth, if the question is multiple choice, it scores each option against the facts it found and picks the best match.

For example, given the question "What is Snort used for?", the system would find the Snort entity in the graph, retrieve facts like "Snort uses Intrusion Detection" and "Snort can detect network attacks", and use those facts to select the correct answer.

What Is the Dataset?
The dataset was created by reading six university cybersecurity lab documents and manually labeling the important concepts and how they connect. The topics covered are Nmap network scanning, penetration testing with firewall and IDS evasion, system security fundamentals, advanced system security, and network security tools.

From these documents, the team identified 963 unique cybersecurity entities across categories including tools, attacks, data types, functions, and system components. They also defined 9 types of relationships such as uses, is a part of, can detect, can harm, and can exploit. These entities and relationships were recorded as 728 individual facts called triples, each in the format of subject, relationship, object.

The dataset also includes annotated training data for building machine learning models that can automatically read new cybersecurity documents and extract entities from them, which would allow the knowledge base to grow over time.

Who Is This For?
Students studying for the CISSP certification or other cybersecurity credentials can use CyberRAG as a study tool that answers questions with referenced facts rather than guesses.

Instructors at universities can use the dataset and source documents as a foundation for building AI-assisted course materials.

Security trainers in organizations can deploy the system to provide employees with a reliable, domain-specific assistant for learning security concepts.

Researchers in AI, natural language processing, or cybersecurity can use the dataset to build better knowledge graphs, train named entity recognition models, or test new question-answering approaches.

The Dataset Files
These files live inside the dataset/ folder. They are the core of the entire project. Everything else depends on them.

dataset/all_entity_info.csv
This file is a list of every cybersecurity concept that was identified across the six lab documents. It has 963 rows, one for each entity. Each row has four columns: a unique ID number, the name of the entity (for example, Snort, Nmap, or SQL Injection), the type of entity (such as tool, attack, feature, or data), and the category (either concept or application). You do not run this file. You open it in Excel or Google Sheets to browse the entities, or the Python scripts read it automatically when building the knowledge graph.

dataset/all_relation_info.csv
This file lists the nine types of relationships that can exist between entities. The relationships are: has_a, can_analyze, can_expose, can_exploit, implements, uses, is_a, can_harm, and part_of. You do not run this file. It is read automatically by the graph-building script. You can open it in Excel to see the full list of relationship types.

dataset/all_triples.csv
This is the most important data file. It contains 728 rows, each representing one fact about the cybersecurity domain. Every row has three columns: the first entity, the relationship, and the second entity. For example, one row says Snort, uses, Intrusion Detection. Another says Snort, can_detect, network attacks. Together these rows form the knowledge graph. You do not run this file directly. The graph-building script reads it automatically. You can open it in Excel to browse the facts.

dataset/triple_doc1.csv
This is a smaller version of the triples file that contains only the facts extracted from the first lab document, which covers Nmap. It has an extra column called Action that provides a short label describing the nature of each relationship. This file is useful if you want to study just the Nmap portion of the dataset in isolation. You can open it in Excel to explore it, or use it as a smaller dataset for testing your own scripts.

The Source Documents
These files live inside the datasource/ folder. They are the original lab documents that the dataset was built from. datasource/textfiles/lab1.txt through lab6.txt These are plain text versions of the six cybersecurity lab documents. Each file covers a different topic. Lab 1 covers Nmap, the network scanning tool. It explains different scan types including TCP, UDP, SYN, and stealth scans, and describes how Nmap scripts work. Lab 2 covers penetration testing against firewalls and intrusion detection systems. It explains how testers use Nmap and Metasploit to probe and evade security defenses. Lab 4 covers system security fundamentals including basic hardening techniques. Lab 5 covers advanced system security topics including authentication and access control. Lab 6 covers network security tools and protocols including IDS and IPS systems. There is also a sixth lab document (lab-cs-cns-20010.docx) covering additional IDS scenarios and Snort rule analysis that does not have a numbered text file but is included in the docx format. You can open and read these files in any text editor. They are the human-readable source material that the dataset was extracted from. datasource/lab-cs-cns-20001.docx through other .docx files These are the original Word document versions of the same six labs. They are formatted versions of the same content as the text files above. Open them in Microsoft Word or Google Docs if you want to read the labs with their original formatting, diagrams, and tables. datasource/csv/lab1.csv through lab6.csv These are structured CSV versions of each lab document, where the lab content has been broken into rows. They are useful if you want to process the lab content programmatically rather than reading the full text files.

The Annotated Training Data
These files live inside the Model/dataprep/ folder. They are used to train machine learning models that can automatically extract cybersecurity entities from text.

Model/dataprep/annotated_BIO.csv
This file contains the lab document text broken into individual sentences, with each word labeled using BIO tagging. BIO stands for Beginning, Inside, and Outside. Every word in every sentence is given a label. If a word is the first word of a cybersecurity entity, it gets a B label such as B-tool or B-attack. If a word is a continuation of an entity, it gets an I label. If a word is not part of any entity, it gets an O label. For example, the sentence "Snort can detect network attacks" would be tagged as: B-tool O O B-attack I-attack, meaning Snort is the beginning of a tool entity, and network attacks spans two words that together form an attack entity. This file is used as training data for a named entity recognition model. If you are a researcher who wants to train a model to automatically read new cybersecurity documents and identify the important terms, this is the file you would use. You would load it into a machine learning framework such as Hugging Face Transformers or spaCy and train a sequence labeling model on it.

Model/dataprep/annotated_data_BI.csv
This file is similar to the BIO file above but uses a simpler tagging scheme that only marks word spans that are part of an entity, without the O tag for non-entity words. Some NER training frameworks prefer this format. Use this file if the framework you are working with expects BI-format annotations rather than BIO.

Model/dataprep/splitdata_final.csv
This file contains the annotated data already divided into a training set and a test set. Using this split ensures that your model evaluation is consistent and reproducible. Use this file when you are ready to train a model and want to measure how well it performs on data it has not seen before.

Model/dataprep/data-preprocess.ipynb
This is a Jupyter notebook that shows the steps used to clean and prepare the raw lab text before annotation. Open it in Jupyter Notebook or JupyterLab by running jupyter notebook in your terminal and navigating to the file. It is useful for understanding how the annotated data was created or for replicating the preprocessing on new documents.

The Python Scripts
These are the runnable files that do the actual work.

kg_builder.py
This is the script that reads the three dataset CSV files and builds the knowledge graph. Run it once before using anything else. To run it, open your terminal, navigate to the project folder, and type: python kg_builder.py When it finishes, it will create two new files: knowledge_graph.pkl and knowledge_graph.json. These are saved versions of the graph so you do not have to rebuild it from scratch every time. You can also import this script into your own Python code to use the graph programmatically. For example: pythonfrom kg_builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder("dataset") kg.build_graph()

Search for an entity
print(kg.search_entities("Snort"))

See what Snort is connected to
print(kg.find_related_entities("Snort"))

Find the connection between two entities
print(kg.get_path_between_entities("Snort", "network attacks")) main_pipeline.py This is the master script that runs the entire system from start to finish in one command. It handles scraping CISSP exam questions, building the knowledge graph, and answering the questions automatically. To run the full pipeline without scraping new questions (using sample questions instead): python main_pipeline.py To run the pipeline and scrape real CISSP questions from the web first: python main_pipeline.py --scrape --max-pages 10 To rebuild the knowledge graph from scratch instead of using a saved version: python main_pipeline.py --rebuild-kg To limit the number of questions it answers (useful for testing): python main_pipeline.py --limit 20 When it finishes, it saves the answers to a file called answers.json and prints a summary showing how many questions were answered and the average confidence score. answer_cissp_questions.py This script is a focused version of the pipeline that only handles answering questions. Use this after you already have a question file ready and have already built the knowledge graph. To run it, type: python answer_cissp_questions.py The script will ask you to specify how many questions to answer. It looks for questions in a file called cissp_questions.json or cissp_questions.csv in the same folder. It then loads the knowledge graph, runs each question through the query engine, and saves the results to two files: cissp_answers.json and cissp_answers.csv. The results include the question, the predicted answer option, a confidence score between 0 and 1, and the specific facts from the knowledge graph that were used to produce the answer. create_interactive_viz.py This script creates interactive HTML visualizations of the knowledge graph that you can explore in a web browser. Nodes represent entities and edges represent relationships. You can click and drag nodes, zoom in and out, and hover over nodes to see details. To run it, type: python create_interactive_viz.py It requires the pyvis library. If you have not installed it yet, run pip install pyvis first. When it finishes, it creates a folder called visualizations and saves several HTML files inside it. Open any of these HTML files in your web browser to explore the graph. It creates a full graph overview, a view focused on Snort and its connections, a view focused on Nmap, and a view showing several key entities together.

The Saved Graph Files These files are created automatically when you run kg_builder.py. You do not create them manually. knowledge_graph.json This is the full knowledge graph saved in JSON format. JSON is a plain text format that is readable by humans and by almost any programming language. Open it in a text editor to inspect its structure, or load it in your own code using the standard json library in Python. This file is useful if you want to use the graph in a language other than Python, or if you want to inspect the raw graph data. knowledge_graph.pkl This is the same graph saved in Python's pickle format. Pickle files load much faster than JSON files, so this is what the Python scripts use when they need to reload the graph quickly. You do not open this file directly. It is loaded automatically by kg_builder.py and main_pipeline.py.

The Documentation Files These are Markdown files you can read in any text editor or on GitHub. IMPLEMENTATION_SUMMARY.md This file gives a detailed technical overview of all the components that were built, including how the web scraper works, how the query engine processes questions, what algorithm it uses to match answers to options, and what the output format looks like. Read this file if you want to understand the technical design of the system or extend it. KG_BUILDER_EXPLANATION.md This file walks through exactly what happens inside kg_builder.py step by step. It explains how the CSV files are read, how entities are indexed, how each triple becomes an edge in the graph, and why a directed multi-graph was chosen. Read this file if you want to understand the graph construction process in detail. KG_BUILDING_VISUAL.md This file contains ASCII diagrams that illustrate how the graph grows as each triple is added. It is a visual companion to the explanation file above. Read it if you learn better from pictures than from prose.

How to Get Started
Install the required Python libraries by running the following command.

pip install pandas networkx nltk numpy
To build the knowledge graph from the dataset files, run the kg_builder.py script. To answer questions using the graph, run the answer_cissp_questions.py script with a file containing your questions. To run the complete pipeline from start to finish, use main_pipeline.py.

Limitations
The system only knows what is in the six source lab documents. Questions about cybersecurity topics not covered in those documents may not get a useful answer.

The way the system finds relevant entities is based on matching keywords, so if a question uses different wording than the dataset, the system may miss the connection.

The system does not reason across multiple steps the way a human expert would. It retrieves facts directly connected to the entities in the question, but cannot chain together several reasoning steps to reach a deeper conclusion.

Future Plans
The team plans to improve entity matching so it understands related words and synonyms, not just exact keyword matches. They also plan to expand the knowledge base by pulling in information from sources like the MITRE ATT&CK framework and NIST security guidelines. Additionally, they aim to integrate a neural reading model on top of the graph retrieval to improve answer accuracy on harder questions.
# AISecKG-Cybersecurity-Dataset
Refer to Paper: 
### [AISecKG : Knowledge Graph Dataset for Cybersecurity Education](https://ceur-ws.org/Vol-3433/paper6.pdf)
  
 * Named-entity annotated data set for cybersecurity entities 
 * Triple dataset to create knowledge graphs for Cybersecurity education
 * Bert Model to extract custom-named entities
 
 * Proposed Ontology for learning cybersecurity :

 * User View :

 ![ontology_user_view](https://user-images.githubusercontent.com/54346120/223224352-f4c5dfea-b843-4ecb-908b-62f1fd51faa5.png)


* Attacker View :


![ontology_attacker_view](https://user-images.githubusercontent.com/54346120/223224642-64b6c708-cbec-4711-a69f-3bfce73388d7.png)


* Security View :


![ontology_security_view](https://user-images.githubusercontent.com/54346120/223224862-d858feba-0947-4b99-97b9-6712751b2f34.png)


_To cite_:
* [MLA] Agrawal, Garima, et al. "AISecKG: Knowledge Graph Dataset for Cybersecurity Education." AAAI-MAKE 2023: Challenges Requiring the Combination of Machine Learning 2023 (2023).

* [BibTex] 
@article{agrawal2023aiseckg,
  title={AISecKG: Knowledge Graph Dataset for Cybersecurity Education},
  author={Agrawal, Garima and Pal, Kuntal and Deng, Yuli and Liu, Huan and Baral, Chitta},
  journal={AAAI-MAKE 2023: Challenges Requiring the Combination of Machine Learning 2023},
  year={2023}
}
