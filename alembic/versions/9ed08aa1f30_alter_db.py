"""alter db

Revision ID: 9ed08aa1f30
Revises: 16da6f2257e8
Create Date: 2015-07-05 21:55:21.512495

"""

# revision identifiers, used by Alembic.
revision = '9ed08aa1f30'
down_revision = '16da6f2257e8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('apscheduler_jobs')
    op.alter_column('company', 'resource_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('company', 'resource_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.create_table('apscheduler_jobs',
    sa.Column('id', sa.VARCHAR(length=191), autoincrement=False, nullable=False),
    sa.Column('next_run_time', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('job_state', postgresql.BYTEA(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=u'apscheduler_jobs_pkey')
    )
    ### end Alembic commands ###