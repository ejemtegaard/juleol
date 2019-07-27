"""empty message

Revision ID: f0ba66f2e9b2
Revises: a85bcd43f2c4
Create Date: 2019-07-26 23:44:38.116470

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0ba66f2e9b2'
down_revision = 'a85bcd43f2c4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('heats',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('tasting_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tasting_id'], ['tastings.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'tasting_id')
    )
    op.add_column('beers', sa.Column('heat_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'beers', 'heats', ['heat_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'beers', type_='foreignkey')
    op.drop_column('beers', 'heat_id')
    op.drop_table('heats')
    # ### end Alembic commands ###
