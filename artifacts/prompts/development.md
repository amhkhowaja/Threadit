DEVELOPMENT STRATEGIES:

Context:

- We already have created the System design, analysis, architecture . 
- all the decisions, planning are in artifacts/docs directory.

Strategies:

- The Development should be decomposed into phases.
- It should be Test driven development including unit tests, integration tests, load tests, deployment test both on actual aws and floci.
- There should be logging for different log level such as debug, info, errors 
- the development should be modular, maintainable, configurable, 
- during the development if there is a new decision, dont take it yourself , always keep me in the loop.
- create a build with makefile to build it on floci or aws 
- proper directory structure should be created before development 
- follow the secure coding guidelines and OWASP top 10 principals during development.
- donot print any vulnerable content in the logging .
- comments should be minimal.
- development style should be future proof.
- take care of the dependency injections, through object oriented principals , abstractions.

- for this use case always consult for senior agents available for any understanding, also the artifacts docs .


Planning:

- plan the development and create a md file:
    -- aws/floci infrastructure as a code
    -- build
    -- service development
    -- deployment

Development:

- Every phase, decompose the phase into number of tasks.
- start implementing 
