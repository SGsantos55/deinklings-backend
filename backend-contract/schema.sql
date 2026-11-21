-- Plain PostgreSQL schema for the Flask backend (no Supabase/RLS dependencies).
-- Derived from the project's original Supabase migration
-- (drizzle/migrations/0000_migration.sql, now removed) but rewritten to run
-- on any Postgres instance, with authorization enforced in the Flask app
-- instead of row-level security policies.

create extension if not exists pgcrypto; -- for gen_random_uuid()

create type app_role as enum ('storyteller', 'creative');

create table users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  password_hash text not null,
  display_name text not null default '',
  role app_role not null,
  created_at timestamptz not null default now()
);

create table listings (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references users(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 120),
  format text not null,
  genre text not null,
  mood text not null default '',
  body text not null,
  logline text not null check (char_length(logline) <= 160),
  synopsis text not null check (char_length(synopsis) <= 2000),
  tags text[] not null default '{}',
  mediums text[] not null default '{}',
  open_to_adaptation boolean not null default true,
  open_to_collaboration boolean not null default false,
  open_to_licensing boolean not null default false,
  cover_url text,
  created_at timestamptz not null default now()
);
create index listings_owner_id_idx on listings(owner_id);
create index listings_format_idx on listings(format);
create index listings_genre_idx on listings(genre);

create table adaptation_requests (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references listings(id) on delete cascade,
  requester_id uuid not null references users(id) on delete cascade,
  owner_id uuid not null references users(id) on delete cascade,
  medium text not null,
  message text not null check (char_length(message) between 10 and 1500),
  status text not null default 'pending' check (status in ('pending', 'accepted', 'declined')),
  created_at timestamptz not null default now(),
  responded_at timestamptz
);
create index adaptation_requests_owner_id_idx on adaptation_requests(owner_id);
create index adaptation_requests_requester_id_idx on adaptation_requests(requester_id);

-- Authorization rules to enforce in the Flask app (there is no RLS here):
--   * A listing can only be created/updated/deleted by its owner
--     (users.role must be 'storyteller' to create one).
--   * An adaptation_requests row can only be created by a 'creative' user;
--     owner_id must be copied server-side from the referenced listing, never
--     trusted from the client.
--   * Only the request's owner_id may change its status
--     (accepted/declined); only requester_id/owner_id may read it.
