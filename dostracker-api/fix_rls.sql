-- Script pour corriger les problèmes de RLS sur la table users
-- À exécuter dans Supabase SQL Editor

-- 1. Vérifier l'état actuel de RLS
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'users';

-- 2. Désactiver RLS sur la table users (solution temporaire pour développement)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- 3. Vérifier que RLS est désactivé
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'users';

-- 4. Alternative: Si vous voulez garder RLS, créer une politique permissive
-- Décommenter les lignes suivantes si vous préférez garder RLS activé

-- CREATE POLICY "Allow public read access" ON users
--   FOR SELECT
--   USING (true);

-- CREATE POLICY "Allow public insert" ON users
--   FOR INSERT
--   WITH CHECK (true);

-- CREATE POLICY "Allow public update" ON users
--   FOR UPDATE
--   USING (true)
--   WITH CHECK (true);

-- CREATE POLICY "Allow public delete" ON users
--   FOR DELETE
--   USING (true);
