import React, { useState } from 'react';
import axios from 'axios';

const Level2AuthPage = () => {
  const [selfie, setSelfie] = useState(null);
  const [idCard, setIdCard] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('selfie', selfie);
    formData.append('id_card', idCard);

    try {
      await axios.post('/api/users/auth/level2/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: `JWT ${localStorage.getItem('access_token')}`,
        },
      });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div>
      <h2>Level 2 Authentication</h2>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={(e) => setSelfie(e.target.files[0])} />
        <input type="file" onChange={(e) => setIdCard(e.target.files[0])} />
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default Level2AuthPage;
