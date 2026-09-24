# Task API repository structure

The Task API follows the shared SparrowX backend structure. `src/database.py` owns PostgreSQL configuration, `src/models.py` owns persistence models, `src/schemas.py` owns API validation, and `src/routes/tasks.py` owns task endpoints. The application starts from `src.main:app`.
