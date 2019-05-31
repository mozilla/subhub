# Backups

## DynamoDB tables
All the DynamoDB tables created via Serverless have Point-In-Time-Recovery (from now on PITR) backups enabled. This kind of backup is completely managed by AWS an consists on incremental backups triggered by modifications to the table. They are billed by space used and are kept and automatically rotated after 35 days, furthermore when a table is deleted AWS triggers an on-demand backup of the table which will be present for 35 days free of charge.

For a more in-depth understanding of PITR visit the official AWS documentation [here](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html).

### Restoring a PITR backup
The process for restoring a PITR backup is straightforward and can de done using AWS UI console or CLI tool, the official documentation describes step by step how to do it [here](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.Tutorial.html). It's recommended to use the AWS console for its simplicity.

When restoring a table a user has to choose: a name for the new database and the point in time (i.e: month, day and time) from when to restore the database.
After some minutes, the backup will be restored into a new database with the name you chose. 

### Restoring from an on-demand backup
On-demand backups are created by AWS when a table is deleted, also when triggered by a user. Restoring an on-demand backup involves the same process that restoring a PITR but instead of choosing the time when the backup was created, the user has to choose the name of the backup. If the backup was automatically created by the system on table deletion, it will be named as the original table plus the suffix "$DeletedTableBackup".

### Disaster recovery
In a disaster recovery scenario, you'd probably want to start using this newly restored table, because DynamoDB does not allow changing the name of a table, at this point there are 2 options: pointing the code to the new restored database or update the old database with the contents of the restored one.

