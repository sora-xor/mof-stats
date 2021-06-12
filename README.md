# mof-stats
SORA Parliament, Ministry of Finance, Department of Data and Statistics

## About
This tool imports history of swap transactions from Substrate node into relational database.

## Usage

### Option 1: Run Substrate node, DB, Import & Web server in docker

1. Clone repository
```bash
git clone git@github.com:yuriiz/mof-stats.git
cd mof-stats/
```

2. Create `.env` file with DB connection settings:

```bash
cat > .env <<EOF
DB_NAME=sora
DB_USER=sora
DB_PASSWORD=secret
EOF
```

3. Run all services
```bash
docker-compose up --scale import=1
```

### Option 2: Run Substrate node & DB in docker but import script natively

1. Clone repository
```bash
git clone git@github.com:yuriiz/mof-stats.git
cd mof-stats/
```

2. Create `.env` file with DB connection settings:

Option 2.1. to import into PostgreSQL
```bash
cat > .env <<EOF
DB_NAME=sora
DB_USER=sora
DB_PASSWORD=secret
DATABASE_URL=postgresql+asyncpg://sora:secret@localhost/sora
EOF
```

Option 2.2. to import into MySQL
```bash
cat > .env <<EOF
DB_NAME=sora
DB_USER=sora
DB_PASSWORD=secret
DATABASE_URL=mysql+aiomysql://sora:secret@localhost/sora
EOF
```

3. Create virtualenv and install requirements
```bash
python -mvenv venv
venv/bin/pip install -r requirements.txt
```

4. Run Substrate node & DB server
```bash
docker-compose up
```

5. Wait for some time until node synchronizes...

6. Run import
```bash
venv/bin/python run_node_processing.py
```

7. Obtain results
```bash
psql -hlocalhost -Usora -c 'select * from swap limit 3;'
```
```
          id          | block |   timestamp   |     xor_fee     | asset1_id | asset2_id |    asset1_amount     |    asset2_amount     |         price         | filter_mode |  swap_fee_amount
----------------------+-------+---------------+-----------------+-----------+-----------+----------------------+----------------------+-----------------------+-------------+-------------------
  4335233996911863155 |  2519 | 1619532174000 | 700000000000000 |         1 |         2 |     1000000000000000 |   586919858573954037 | 0.0017038101290859566 | SMART       |     3000000000000
 17382568824412415775 |  2803 | 1619533878000 | 700000000000000 |         3 |         1 |  1000000000000000000 |  1951281993032052883 |    0.5124835895431611 | XYKPool     |  5901755306013563
 13713375740121947297 |  2824 | 1619534004000 | 700000000000000 |         3 |         1 | 18005766125156550509 | 20000000000000000000 |    0.9002883062578275 | XYKPool     | 60180541624874623
(3 rows)
```

### Option 3: Run import from node on other host to DB on another host
1. Clone repository
```bash
git clone git@github.com:yuriiz/mof-stats.git
cd mof-stats/
```

2. Create virtualenv and install requirements
```bash
python -mvenv venv
venv/bin/pip install -r requirements.txt
```

3. Run import

Assuming DB in PostgreSQL running at 1.1.1.1 and archive Substrate node is running at 2.2.2.2 executable command would be:
```bash
env DATABASE_URL=postgresql+asyncpg://user:password@1.1.1.1/dbname SUBSTRATE_URL=ws://2.2.2.2:9944 venv/bin/python run_node_processing.py
```

### Runing web server

After import is done it is possible to run web server serving last pair prices:
```bash
venv/bin/python webapp.py
```

```bash
curl -s localhost:8888|jq|head -n12
```
```json
{
  "0x0200000000000000000000000000000000000000000000000000000000000000_0x0200060000000000000000000000000000000000000000000000000000000000": {
    "base_id": "0x0200060000000000000000000000000000000000000000000000000000000000",
    "base_name": "Dai",
    "base_symbol": "DAI",
    "quote_id": "0x0200000000000000000000000000000000000000000000000000000000000000",
    "quote_name": "SORA",
    "quote_symbol": "XOR",
    "last_price": 0.001537295942369473,
    "base_volume": "2910264628433435323",
    "quote_volume": "1893397842998926724472"
  },
```

```bash
curl -s localhost:8888/XOR-PSWAP|jq
```
```json
{
  "base_id": "0x0200000000000000000000000000000000000000000000000000000000000000",
  "base_name": "SORA",
  "base_symbol": "XOR",
  "quote_id": "0x0200050000000000000000000000000000000000000000000000000000000000",
  "quote_name": "Polkaswap",
  "quote_symbol": "PSWAP",
  "last_price": 1209.3185507219912,
  "base_volume": 12403679734379872,
  "quote_volume": 15000000000000000000
}
```


### Benchmarks

#### Importing first 30,000 blocks to PostgreSQL
```bash
time venv/bin/python run_node_processing.py
```
```
100%|█████████████████████████████████████| 30000/30000 [19:31<00:00, 25.61it/s]

real	19m33.305s
user	7m32.696s
sys	0m5.870s
```
#### Importing first 30,000 blocks to MySQL
```bash
time venv/bin/python run_node_processing.py
```
```
100%|█████████████████████████████████████| 30000/30000 [22:05<00:00, 22.63it/s]

real	22m8.405s
user	8m6.946s
sys	0m6.163s
```
