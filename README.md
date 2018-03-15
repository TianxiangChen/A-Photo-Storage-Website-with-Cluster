# A-Photo-Storage-Website-with-Cluster
This repo just for displaying the sample code. It doesn't have some config file to make the app run properly.
For a demo, please contact me.

This project:
- Written in Python with Flask and deployed on the Amazon EC2
- Allow users to sign up/in his/her account, upload photos and storeinside the account
- Use 3 different types of EC2 instances by different AMI: one for thewebsite(UserUI), one for Database (MySQL in EC2) and one forManagerUI (Manage the scaling of the User instance and data storage)
- MySQL as database setup in one EC2 instance, S3 as file storage
- Manager Instance can manually expand/shrink number of user instances(Cluster configured with Nginx and Gunicorn) or set auto-scaling algorithm for load balancing and reset the S3 storage using boto3
- Use Redis for auto-scaling parameters storage
- Setup still available, can demo if needed
