SYSTEM DESIGN REQUIREMENT:

Functional requirements:

- Users can create posts (with at least a title and body).
- Users can reply to posts (threaded or flat, your choice).
- Users can view a list of posts and view an individual post with its replies.
- Persist in data so it survives a server restart (a real database, file storage, or
embedded DB - your choice).

Additinal functional requirements:

- TBD : User can upload the image as part of post body
- All write operation would require an auth whereas read operation assuming at this stage is public.


Non Functional requirements:

- Traffic requirement : billions of users using , reading the posts, reading comments, writing posts without any downtime .
- Assume Commenting is write heavy , where as posts reading and checking comments (replies) are read-heavy, there for CQRS pattern of microservice architecture would fit the use case.
- We prioritize:
    -- High availability
    -- Scalability
    -- Low Latency
    -- Intense throughput
    -- Partition tolerance 
    -- Resilience
    -- Mainly the architecture and caching strategies as part of low-latency requirements]
    -- Rate limiting as well for high throughput attack on a single service, let say read operation (high availablity, latency requirement)
    -- We have to think about Caching as well
    -- database schema should be horizontally scalable and future proof


- Tradeoffs:
    -- Ofcourse due to CAP theorem , we are choosing AP and consistency could not be prioritized and for this use case eventual consistency is acceptable.

- To be decided TBD:
    -- addition of subscriber list , so that if user have 50million subscriber then read become very expensive which is a celebrity problem. Also slow - write 

Tech Stacks:

- Since, we dont want to solve already solved problems we are going to use AWS Managed Services for the implementation.
- The key is, in this project we dont more implementation complexity rather an infrastructure which is configurable using terraform.

Here is what i think:

- For highly intense throughput write and horizontally scalable (NoSQL) db which automatically support sharding , autoscalability, partitioning. Good for both read and write heavy apps.
- TBD : image upload goes to S3.
- TBD : Elasticache for region based caching (may be phase 2)
- We can use cloudfront + WAF for caching , ratelimiting, image delivery, auth.
- AWS fargate for service deployments
- We create the same code base of service and deploy the same service twice based on the role read and write to balance the load using CQRS .

ANALYSIS AND PLANNING:
- First analyze the requirements and my mental model above and critique it based on that.
- This is very important to delicately understand the scale of billions of users and decomposition of microservices based on the use case .
- if there is any better idea for certain problem mention that in the analysis document 
- create the detailed analysis document in artifacts/docs/ANALYSIS.md

- The planning should be based on the phases , all TBDs can come in the phase 2 or phase 3 . 
- the required first phase is to create the infrastructure, database schema, api contracts with timestamps, and future proof .
- Decompose the plans into task for the development and deployment.
- The planning document should be saved in artifacts/docs/PLANNING.md

ARCHITECTURE:
- After analyzing and structuring the planning , create system design architecture md file as artifacts/docs/SYSTEM_ARCHITECTURE.md
- Also document the Sequence diagram as well in above document.

FINAL NOTES:
- keep me in the loop for any key decision.
- donot hallucinate.


