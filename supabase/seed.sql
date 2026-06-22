-- Run after migration.sql and migration_v2_jobs.sql
truncate public.demo_seekers cascade;
truncate public.sample_jds cascade;

insert into public.demo_seekers (name, scores) values ('Abigail Hernandez', '{"effective_communicator": 70, "global_citizen": 80, "creative_innovator": 85, "critical_thinker": 72, "reflective_future_focused": 60, "career_ready": 35}'::jsonb);
insert into public.demo_seekers (name, scores) values ('Zackary Smith', '{"effective_communicator": 85, "global_citizen": 60, "creative_innovator": 70, "critical_thinker": 90, "reflective_future_focused": 80, "career_ready": 75}'::jsonb);
insert into public.demo_seekers (name, scores) values ('Emily Chen', '{"effective_communicator": 95, "global_citizen": 85, "creative_innovator": 60, "critical_thinker": 75, "reflective_future_focused": 90, "career_ready": 85}'::jsonb);
insert into public.demo_seekers (name, scores) values ('Jamal Washington', '{"effective_communicator": 60, "global_citizen": 95, "creative_innovator": 80, "critical_thinker": 65, "reflective_future_focused": 70, "career_ready": 90}'::jsonb);
insert into public.demo_seekers (name, scores) values ('Sophia Patel', '{"effective_communicator": 80, "global_citizen": 75, "creative_innovator": 90, "critical_thinker": 85, "reflective_future_focused": 65, "career_ready": 80}'::jsonb);

insert into public.sample_jds (id, title, body, sort_order) values ('data_platform_engineer', 'Data Platform Engineer (Heads-Down, Backend)', $jd$Data Platform Engineer (Heads-Down, Backend)

ABOUT THE ROLE

This is a deep, heads-down engineering role. To be clear up front: you will NOT
present to clients or stakeholders, there is no public speaking, and we do not
expect you to write reports, blog posts, or polished documentation. Communication
overhead is kept to an absolute minimum so you can focus on the systems. We are
also not looking for "innovative disruptors" or big-picture creative ideation,
this is about reliable, repeatable execution, not inventing new products.

WHAT YOU WILL DO

Build and maintain batch and streaming data pipelines that move billions of rows
per day. You will diagnose flaky pipelines, root-cause production incidents, and
reason carefully through ambiguous data-quality failures until you find the real
cause. Expect to weigh trade-offs between cost, latency, and correctness on a
daily basis.

Because our engineering pods run in Sao Paulo, Berlin, and Bangalore, your commits
and on-call handoffs have to line up with their working hours and public holidays,
and you will adjust your schedule and review etiquette to fit each pod's norms.

WHAT WE NEED

Expert-level SQL and Python. Hands-on experience with Airflow, dbt, Kafka, and
Spark. Comfortable owning infrastructure in AWS. You should be the kind of
engineer who quietly keeps the platform running.

WHAT WE ARE NOT

Again: this is not a client-facing or evangelism role. No stakeholder management,
no conference talks, no "thought leadership."
$jd$, 0);
insert into public.sample_jds (id, title, body, sort_order) values ('fbi', 'JOB SUMMARY', $jd$JOB SUMMARY 

The FBI is looking for Police Officers and seeking qualified candidates from a variety of backgrounds and professional disciplines who are committed to combating crime and terrorism while protecting the American public. All New Police Officers will be offered their working location based on the needs of the Bureau and must sign a two-year service agreement agreeing to stay in the Police Officer Program and their office of assignment location for a period two years. #LI-FBI

LOCATION: Washington, DC; New York, NY; Clarksburg, WV

KEY REQUIREMENTS

Must be a U.S. citizen.
Must be at least 21 years of age.
Must be able to attend and pass the Police Officer Selection System (POSS) written test and panel interview. Applicant will be responsible for all travel expenses associated with travel to and from the testing location.
Must be able to pass a U.S. Government physical exam.
Must have (or be able to obtain) a valid driver’s license.
Must become proficient in the use of a firearm and various other weapon system.
Must be able to obtain a Top Secret clearance.
Selectee will be required to complete a Financial Disclosure Form.
Must attend and complete training at the Federal Law Enforcement Training Center (FLETC) in Glynco, GA. Exceptions may be made on a case-by-case basis.
Must adhere to a service agreement starting from the effective date of their appointment as an FBI Police Officer.
Must be willing to work nights/weekends/holidays (shift work).
About Us

FBI Police Officers protect public safety by maintaining order, responding to emergencies, protecting people and property, enforcing motor vehicle and criminal laws and promoting good community relations. You will monitor, report and investigate suspicious persons and situations, as well as safety hazards and unusual or illegal activity in patrol areas. You will identify, pursue and arrest suspects and perpetrators of criminal acts.

About You

You have a background or interest in Criminal Justice, Law Enforcement or Security Operations. You are interested in beginning a career with the FBI and gaining professional experience in protective operations at America’s premier law enforcement agency. You have experience or desire to protect and secure people and real property.

If you are a recent graduate with a background in Criminal Justice, Security or Political Science, a municipal or military Police Officer looking for federal employment, or a Protective Security professional looking for career advancement, this could be the opportunity for you. We welcome retired law enforcement officers to re-enter the workforce as an FBI Police Officer.

As an FBI Police Officer, you will play a key role in keeping the FBI and surrounding areas secure. FBI Police Officers provide service to those in their duty stations and if necessary, travel to aid in times of crisis.

PHYSICAL DEMANDS 

The work requires considerable and strenuous physical exertion such as frequently climbing stairs and ladders; lifting weapons, other objects, and people weighing over 50 lbs.; crouching, crawling, and or running in pursuit of violators and trespassers; and defending oneself and others against physical attack. Agility and dexterity coupled with the strength to pursue, apprehend, and detain/arrest uncooperative suspects is additionally needed. Considerable physical effort is required to subdue, disarm, and arrest violent or potentially violent persons suspected of crimes. Involved persons may be armed with knives, guns, or other dangerous weapons. The work additionally requires continuous mental focus. Physical demands can be potentially amplified through conditions such as extreme weather and occasional long periods of overtime that the incumbent may be exposed to.

WORK ENVIORNMENT 

The work environment regularly involves high risks with exposure to potentially dangerous situations inherently associated with the provision of law enforcement, security, and emergency medical care services. A range of safety precautions are taken in situations where there is specific risk of attack, as well as those having conditions that are uncontrollable. The work involves exposure to extreme weather conditions; dangerous and hazardous situations; materials such as toxic gases, fumes, high explosives; and a variety of illnesses due to the medical aspects of the job. Assignments can also include regular and recurring exposure to extreme discomforts and unpleasantness, particularly during inclement weather or extended periods of traffic and patrol duties. Required duties subject the incumbent to extreme personal danger (e.g. possible physical attack, mob assaults, sniper attacks), which may or may not occur where conditions are able to be controlled. Incumbent may be assigned to both traditional and non-traditional shifts and asked to work odd or extensive hours in connection with special assignments or emergency situations.

MAJOR DUTIES:

As an FBI Police Officer you will:

Provide public safety by maintaining order, respond to emergencies, protect people and property, enforce motor vehicle and criminal laws, and promote good community relations.
Monitor, note, report, and investigate suspicious persons and situations, safety hazards, and unusual or illegal activity in patrol area.
Identify, pursue, and arrest suspects and perpetrators of criminal acts.
Investigate traffic accidents and other accidents to determine causes and to determine if a crime has been committed.
Record facts to prepare reports that document incidents and activities.
Check for proper identification of pedestrian and vehicular traffic prior to admittance to secure space at Stationary posts. Provide screening of vehicles for the detection of explosive devices.
Respond to a variety of alarm situations, protect and safeguard information and material affecting national security and defense and protects people and their civil rights from a wide variety of dangerous and hostile situations.
For more information regarding the FBI Police Officer position, please review FBI Police Officers: An Inside Look.
QUALIFICATIONS AND EVALUATIONS

Please ensure that your specialized experience and requirements are clearly identifiable in your resume. Your application will be evaluated using the FBI’s Candidate Rating Procedures. Your resume and supporting documents will be reviewed to verify that you meet the job qualifications listed in this announcement and will be compared against your responses to the online assessment questionnaire. Applicants must meet the qualification requirements by the closing date of this announcement. 

If you are deemed Most Competitive, you will be referred to the selecting official for further consideration.

The competencies will be used in a Structured Resume Review to objectively evaluate applicant resumes. Do not provide a separate narrative written statement. Rather you must describe in your resume how your past work experience demonstrates that you possess the competencies identified below. Your resume should demonstrate that you possess the following competencies.  

Competencies

Communication
Problem Solving/ Judgement 
Conflict Solving 
Public Safety and Security 
Interpersonal Ability 
Specialized Experience (SE)

GS-7: Applicants must possess at least one (1) year of specialized experience equivalent to the GS-5 grade level. SE is defined as:

Independently performing routine, recurring kinds of fixed post and patrol assignments to include: commonly accepted installation traffic laws and rules; regulating access to Federal buildings and conduct of visitors and employees.
OR

Have successfully completed a full 4 year course of study leading to a bachelor's degree. Education completed in foreign colleges or universities may be used to meet the above requirement if you can show that the foreign education is comparable to that received in an accredited educational institution in the United States. All degrees must be from an accredited college or university.
 

GS-9: applicants must possess at least one (1) year of specialized experience equivalent to the GS-7 grade level. SE (in addition to the above) is defined as:

Experience that provided knowledge of a body of basic laws and regulations, law enforcement operations, practices, and techniques and involved responsibility for maintaining order and protecting life and property.
Creditable specialized experience may have been gained in work on a police force; through service as a military police officer; in work providing visitor protection and law enforcement in parks, forests, or other natural resource or recreational environments; in performing criminal investigative duties; or in other work that provided the required knowledge and skills.
Experience in writing incident and investigative reports and issue citations.
 

GS-10: applicants must possess at least one (1) year of specialized experience equivalent to the GS-9 grade level. SE (in addition to the above) is defined as:

Experience performing law enforcement work in the protection of life, property and the civil rights of individuals; with secondary mission being the protection of Government property and national security information from acts sabotage, espionage, terrorism, trespass, theft, fire, and accidental and/or willful damage and destruction.
Experience responding to a wide variety of calls concerning very serious and sensitive situations involving disorderly conduct, deranged persons, and similar occurrences.
Experience maintaining law and order and provides a variety of protective services for employees and visitors on Federal property.
 

GS-11: applicants must possess at least one (1) year of specialized experience equivalent to the GS-10 grade level. SE (in addition to the above) is defined as:

Experience with operations and techniques used in preventing or resolving offenses. Well-versed in the methods and procedures used in conducting preliminary investigations of a wide array of offenses, ranging from the most minor to felony and capital crimes.
Experience in patrolling operations, tactics, and optimal strategies for handling unruly persons, violent unruly crowds involved in planned or impromptu demonstrations or riots, detection of explosives, presence of illegal drugs, hostage situations, counterterrorist operations, vehicular and pedestrian accidents, safety violations, and other serious accidents.
HOW TO APPLY

For detailed instructions related to applying, uploading documents, withdrawing an application or updating your application, please review instructions on How to Apply.  If applying online is a hardship, please use the contact information listed in the vacancy announcement prior to the closing date for assistance.

REQUIRED DOCUMENTS

To apply to this position, interested applicants must provide a complete application package by the closing date which includes:

Utilizing the Resume Builder, outline your relevant work experience and associated start and end dates. Uploaded resumes will not be reviewed or used for qualification purposes. 
A complete assessment questionnaire
Other supporting documents (if applicable):
College transcripts, if qualifying based on education or if there is a positive education requirement
Former civilian Federal employees must submit a copy of your MOST RECENT SF-50 (Notification of Personnel Action) showing your tenure, grade and step, salary, and type of position occupied (i.e., Excepted or Competitive); or similar Notification of Personnel Action documentation, i.e., Transcript of Service, Form 1150, etc. This is a requirement to verify your Time in Grade (TIG). Actions such as promotion, within grade increase, or reassignment actions must be submitted as your most recent SF 50.
Most recent Performance Appraisal; not applicable to current FBI employees
Veterans: DD 214; Disabled Veterans: DD 214, SF-15, and VA letter dated 1991 or later
Memorandum for Record (MFR): Work performed outside assigned duties (that would not normally be documented on an SF-50, i. e., back-up duties), has to be documented in detail by an immediate supervisor in order to receive full credit for amount of time worked in that position. If no documentation is furnished no credit will be given for time worked in that position. The following notations must be specified in the documentation:
Percent of time worked in the particular position (cannot conflict with main duties.
The month/year work began
Frequency worked (i.e., daily, monthly, etc.)
Specific duties performed
Attach the Memorandum for Record to your application in the “Cover Letters and Attachments” section of My Career Tools on the Careers Home page. Please upload the attachment as type “Other.”

While applicants might see these documents in their profile, HR Specialists may be unable to access them. Therefore, all applicants MUST upload another copy to ensure that staffing units can review the complete application.

Please note: Failure to provide the necessary and relevant information required by this vacancy announcement may disqualify you from consideration. Incomplete applications will not be supplemented with additional requests for information; your application will be evaluated solely on the information you submit. You must complete the application process and submit all required documents by 11:59 p.m. (ET) on the announcement’s closing date.

WHAT TO EXPECT NEXT

Once your complete application is received, we will conduct an evaluation of your qualifications and determine your ranking. The Most Competitive candidates will be referred to the hiring manager for further consideration and possible interview. You will be notified of your status throughout the process.

ADDITIONAL INFORMATION

The FBI is in the Executive Branch of the federal government. It is one of the components of the Department of Justice (DOJ). The FBI is the principle investigative arm of the DOJ. All FBI positions are in the excepted service.
Applicants must be U.S. citizens and consent to a complete background investigation, urinalysis, and polygraph. You must be suitable for Federal employment; as determined by a background investigation.
Positions with fitness for duty requirements or those that require international travel may require proof of certain vaccinations.
Management may select any grade for which this position has been announced.
Identification of promotion potential in this announcement does not constitute a commitment or an obligation on the part of management to promote the employee selected at some future date. Promotion will depend upon administrative approval and the continuing need for an actual assignment and performance of higher-level duties. 
If you are selected, you will be required to serve a two-year probationary period. Probationary employees are precluded from being considered for all job opportunities until 12-months of their 24-month probationary period has concluded. Probationary Employees may be considered for competitive vacancies that are advertised within their respective division or field office after serving 90 days within the FBI.
Veterans' Preference

If you are entitled to veterans' preference, you should indicate the type of veterans' preference you are claiming on your resume and application. Your veterans' preference entitlement will be verified by the employing agency.

Nepotism

Nepotism is the act of favoring relatives in the hiring process and is prohibited by law. Public officials are prohibited from hiring or promoting relatives or relatives of officials in their chain of command, as well as actively or indirectly endorse a relative’s appointment or promotion. During the hiring process, all selected candidates and FBI hiring managers will be required to certify they are not related to anyone involved in the hiring process.

Reasonable Accommodation

The FBI provides reasonable accommodations to qualified applicants with disabilities. If you require a reasonable accommodation during the application and/or hiring process, please contact the Office of Equal Employment Opportunity Affairs (OEEOA) Reasonable Accommodation (RA) Program by email at REASONABLE_ACCOMMODA@fbi.gov, phone at 202-324-2158, or fax at 202-324-3976. This email address is for reasonable accommodation requests only. Do not send applications or unrelated inquiries to this address, as they will not be considered.

Equal Employment Opportunity

The FBI is an Equal Opportunity Employer, and all qualified applicants will receive consideration for this vacancy. Unless explicitly authorized by law, selection will be made without regard to, and there will be no discrimination because of, color, race, religion, national origin, marital status, parental status, physical or mental disability, genetic information, age (40 or over), sex, pregnancy and related conditions, or on the basis of personal favoritism, or any other non-merit factors.

Benefits

The Bureau matches your dedication with a commitment to professional growth, a supportive work environment, and a robust benefits package that prioritizes you. As a member of our team, you’ll enjoy comprehensive health and life insurance benefits, paid vacation, sick leave, and federal holidays. For more details about benefits available to all federal employees, visit the Office of Personnel Management’s website.$jd$, 1);
insert into public.sample_jds (id, title, body, sort_order) values ('frontend_developer', '# Job Title: Senior Frontend Developer (React/TypeScript)', $jd$# Job Title: Senior Frontend Developer (React/TypeScript)

We are looking for a creative and innovative Frontend Developer to join our team. 

Key Responsibilities:
- Design and implement highly interactive and visually appealing user interfaces.
- Collaborate with cross-functional teams to solve complex technical problems.
- Communicate technical concepts clearly to non-technical stakeholders.
- Drive innovation in our frontend stack and mentor junior developers.

Requirements:
- Strong experience with React, TypeScript, and modern CSS.
- Demonstrated ability to think critically about user experience.
- Proactive approach to learning and professional development.
- Strong communication skills and a team-player mindset.
$jd$, 2);
insert into public.sample_jds (id, title, body, sort_order) values ('intl_coordinator', '# Job Title: International Operations Coordinator', $jd$# Job Title: International Operations Coordinator

We are seeking a Global Citizen with a passion for cross-cultural collaboration to manage our international projects.

Key Responsibilities:
- Coordinate operations across multiple time zones and cultures.
- Reflect on current processes and propose future-focused improvements for global scalability.
- Ensure all projects comply with international standards and ethical guidelines.
- Build and maintain relationships with partners in Europe, Asia, and South America.

Requirements:
- Strong understanding of global markets and cultural nuances.
- Exceptional organizational skills and the ability to manage complex, international logistics.
- Reflective thinker who can adapt to rapidly changing global environments.
- Career-ready professional with at least 3 years of experience in international business.
$jd$, 3);
insert into public.sample_jds (id, title, body, sort_order) values ('junior_data_analyst', '# Job Title: Junior Data Analyst', $jd$# Job Title: Junior Data Analyst

We are looking for a recent graduate who is Career Ready and has a strong foundation in critical thinking.

Key Responsibilities:
- Collect and analyze large datasets to identify trends and patterns.
- Present data-driven insights to help the team make informed decisions.
- Maintain data integrity and follow strict quality control procedures.
- Participate in regular training sessions to stay current with industry tools.

Requirements:
- Bachelor's degree in Mathematics, Statistics, or a related field.
- Excellent critical thinking and problem-solving skills.
- Ability to communicate complex data findings in a simple way.
- Highly organized and detail-oriented.
- Ready to launch a career in a fast-paced corporate environment.
$jd$, 4);
insert into public.sample_jds (id, title, body, sort_order) values ('moomoo', 'About Futu US Inc.:', $jd$About Futu US Inc.:

Futu US Inc. stands at the forefront of financial services, housing two SEC registered broker-dealers alongside a cryptocurrency brokerage — all operating under the reputable wing of Futu Holdings Limited (Nasdaq: FUTU).

Our core mission revolves around innovating the investing landscape through a digitized brokerage and wealth management platform that's designed to elevate the investment experience.

Here's a closer look at our key entities:

Futu Clearing Inc.: An SEC registered FINRA member dedicated to delivering top-tier clearing and execution services globally.
Moomoo Financial Inc.: As an SEC registered FINRA member, we provide retail investors access to both U.S. and Asian securities markets, ensuring your investment journey is backed by expertise.
Moomoo Technology Inc.: Offering a data-rich trading platform, we provide unparalleled insights and tools to enhance your trading strategies. Note that this entity is not a licensed broker-dealer.
For deeper insights into our entities and affiliates, explore or to discover the future of investing with confidence and innovation.

About our role:

We are looking for a highly motivated and outgoing Financial Customer Experience Associate to support moomoo's in-person activations in our NYC Brand Store. In this role, you will be driving sales, building customer relationships, and handling live customer support. This role combines financial expertise, client relationship management, and event leadership to deliver an exceptional in-person customer experience. You will drive client acquisition, support store activations, and ensure compliance with FINRA and SEC regulations. This is a hands-on position perfect for someone who thrives in high-energy environments, excels at client engagement, and has a deep passion for finance and the U.S. stock market.


Requirements

Key Responsibilities:

Financial Expertise - Learn and maintain a deep understanding of moomoo's history, mission, product features, trading tools, and customer promotions to effectively communicate value to clients
Sales & Promotions Management - Support the on-site sales and promotion efforts
Client Support - Provide exceptional client support by answering incoming questions about moomoo products and services
Sales & Inventory Tracking - Track and report merchandise inventory, sales, and customer conversion data each day
Financial Market Awareness - Stay current on market news, trends, and economic events, and effectively communicate relevant insights to customers
Compliance - Ensure all marketing and sales activities comply with FINRA and SEC guidelines
Qualifications:

Must have or be willing to get SIE upon being hired. FINRA Series 7 and 63 licenses required for the position: preferred upon hiring but must be obtained within 180 days of hire.
Must have knowledge of options and trading strategies
1+ years of experience in sales and/or customer service within a financial services company
Strong personal trading experience (preferred)
In-depth knowledge of FINRA and SEC marketing guidelines
Deep understanding of trading products, services, and the U.S. stock market
Excellent leadership, communication, and customer engagement skills
Ability to work evenings, weekends, and holidays as required

Benefits

What We Offer:

Competitive salary and performance-based bonuses.
Comprehensive benefits package, including health, dental, and retirement plans.
Opportunities for professional growth and development.
A dynamic and collaborative work environment.
Base pay for a successful applicant will depend on a variety of job-related factors, which may include education, training, experience, location, business needs, or market demands. The expected salary range for this role is $50,000-$70,000. This role is also eligible to participate in our discretionary bonus plan.

Disclaimer

The above information in this job description has been designed to indicate the general nature and level of work performed by employees within this classification. It is not intended to contain or be interpreted as a comprehensive inventory of all duties, responsibilities, and qualifications required of employees assigned to this job.

Employment with Futu Holdings Limited, including all subsidiaries, is on an at-will basis. This means that either the employee or the Company may terminate the employment relationship at any time, with or without notice and with or without cause, subject to applicable law. Nothing in this job posting or description should be construed as creating an express or implied contract of employment or guarantee of employment for any specific duration.

Futu Holdings Limited, including all subsidiaries, is an equal opportunity employer, and all qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability status, protected veteran status, or any other characteristic protected by applicable law.$jd$, 5);
insert into public.sample_jds (id, title, body, sort_order) values ('tiktok', 'Full job description', $jd$Full job description
Corporate Functions

Technology Internal Audit Lead - Product Technology & Trust and Safety

Location: Los Angeles

Employment Type: Regular

Job Code: A154697A

Responsibilities

Team Introduction:
Internal Audit is a global function responsible for providing independent assurance and evaluating the company's risk management, governance and internal control processes to determine if they are designed and operating effectively. The Internal Audit team plans and executes audit projects according to our risk-based audit plan by evaluating financial, compliance, operational, and IT processes and controls. We work with business functions in addressing risks and improving the control environment through timely and comprehensive audit work and tracking of remediation actions until completion.

Position Summary:
We are looking for an experienced technology professional to join us as Technology Audit Lead. This individual will contribute to the ongoing development of the Global Technology Audit function and TikTok's efforts to enhance its risk management capabilities in support of the company's business objectives. The individual will be part of the Global Technology Audit team and utilize innovative assurance methods to impact and influence positive business outcomes across products such as TikTok, TikTok LIVE, Local Services and CapCut, as well as Trust & Safety.

Responsibilities:
Audit Delivery: Lead planning and execution of technology and integrated audits supporting technology platforms and infrastructure underpinning core products, product security, LLM powered content moderation, software development lifecycle and governance. Evaluate application security, effectiveness of machine learning models, and assess information security risk management for internally built systems and models.
Data Analytics / AI: Leverage data analytics to detect risk signals and unearth insights. Apply AI technologies/Machine Learning (ML) to develop innovative AI-based audit solutions and perform audit testing. Communicate issues and recommendations to senior management. Collaborate with risk owners to ensure risk mitigation plans are developed and completed, tracking and reporting on the progress of the remediation plans on a regular basis.
Technology Risk Assessment: Assist in analysis and identification of emerging technology risks for TikTok. Develop and maintain subject matter expertise in one or more technology domains. Ability to grasp complex, home grown technology stack, comfortable speaking with engineers and product teams.
Stakeholder Relationships: Develop and maintain collaborative working relationships with management, understand the business to provide value-added services, and establish credibility as a management consultant and internal controls resource. Partner with engineering and product teams to advise on design and implementation of technology solutions.
Professional Development: Continually expand knowledge of the audit profession, industry, and company products through self-study, research, and continuing education efforts. Develop innovative methodologies for auditing new technologies and services.
Quality Assurance: Ensure the overall quality and consistency of audit work, adhering to department and professional standards. Continuously seek opportunities for audit process improvement.
Qualifications

Minimum Qualifications:
More than 5 years of relevant experience in product security, application security, security operations, technical or privacy program management preferably within the technology sector (social media, fintech, infrastructure & cloud providers etc.) and consulting.
Proven ability to work in a fast-paced environment with a product centric culture.
Strong understanding of security fundamentals across various cyber domains: product security, application security, data security or web security
Experience in one or more software or data engineering domains: large scale distributed or parallel systems, microservice architecture, data pipeline and infrastructure
Experience in implementing or evaluating technology and automation in a DevOps environment. Knowledge of logging technologies, system monitoring, and security event management
Proven analytical ability to assess complex technology environments against risk assessment outcomes, industry best practices, internal standards and external regulatory requirements.
Excellent problem solving, critical thinking, collaboration and communication skills combined with the ability to provide a credible technical challenge to the business.
Preferred Qualifications:
Internal Audit experience is preferred but not required
Solid background and experience working with one or more of the following areas:
Major programming languages and frameworks (e.g. Python, C# .NET, JavaScript, node.js, Java)
Source code and DevOps management tools (e.g., Gitlab, Github, Bitbucket)
Common application and infrastructure security vulnerabilities and mitigations (OWASP Top 10, CWE 25).
Cloud platforms (e.g., AWS, Google Cloud Platform)
Database technologies (e.g., SQL, Oracle, SQL Server, MongoDB, Redis, , Elasticsearch)
Professional certifications such as CISSP, CISM, CISA, CRISC, or CIA.
Experience in the digital advertising and/or E‑commerce domain.
Experience working in a global organization and managing projects across different time zones.$jd$, 6);
