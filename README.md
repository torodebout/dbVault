# dbVault

a command-line database backup tool supporting PostgreSQL and MongoDB with local and AWS S3 storage options.

contributions welcome! thank you,

## Features

- database Support: PostgreSQL and MongoDB
- storage Options: Local and AWS S3
- compression: gzip compression for backup files

### Database Dependencies

#### macOS

```bash
# postgreSQL deps
brew install postgresql

# mongodb deps
brew install mongodb/brew/mongodb-database-tools
brew install mongosh
```

## Installation

```bash
git clone https://github.com/torodebout/dbVault.git && cd dbVault && bash scripts/install.sh
```

### Test Connections

```bash
# test all available connections (default)
dbvault test --config config.yaml --env-file .env
```

### Backup

```bash
# local backup
dbvault backup --config config.yaml --env-file .env --storage local
# S3 backup
dbvault backup --config config.yaml --env-file .env --storage s3
```

### List Backups

```bash
# list local backups
dbvault list-backups --storage local --config config.yaml --env-file .env
# list S3 backups
dbvault list-backups --storage s3 --config config.yaml --env-file .env
```

### Restore Database

```bash
# restore from local backup
dbvault restore --backup backup_20240703_120000.gz --config config.yaml --env-file .env

# restore from S3 backup (automatic download)
dbvault restore --backup backup_20240703_120000.gz --config config.yaml --env-file .env --storage s3
```
