import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ProfilePage = () => {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      const { data } = await axios.get('/auth/users/me/', {
        headers: {
          Authorization: `JWT ${localStorage.getItem('access_token')}`,
        },
      });
      setProfile(data);
    };

    fetchProfile();
  }, []);

  if (!profile) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>Profile</h2>
      <p>Username: {profile.username}</p>
      <p>Email: {profile.email}</p>
      <p>Phone Number: {profile.phone_number}</p>
      <p>Points: {profile.points}</p>
      <p>Authentication Level: {profile.authentication_level}</p>
      <p>Tournaments Played: {profile.tournaments_played}</p>
    </div>
  );
};

export default ProfilePage;
