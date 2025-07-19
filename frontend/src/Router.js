import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import TournamentsPage from './pages/TournamentsPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import Level2AuthPage from './pages/Level2AuthPage';
import Level3AuthPage from './pages/Level3AuthPage';

const Router = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tournaments" element={<TournamentsPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/auth/level2" element={<Level2AuthPage />} />
        <Route path="/auth/level3" element={<Level3AuthPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;
