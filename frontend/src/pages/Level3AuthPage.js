import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Level3AuthPage = () => {
  const [video, setVideo] = useState(null);
  const [textToRead, setTextToRead] = useState('');

  useEffect(() => {
    const fetchTextToRead = async () => {
      const { data } = await axios.get('/api/users/auth/level3/text/', {
        headers: {
          Authorization: `JWT ${localStorage.getItem('access_token')}`,
        },
      });
      setTextToRead(data.text_to_read);
    };

    fetchTextToRead();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('video', video);

    try {
      await axios.post('/api/users/auth/level3/', formData, {
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
      <h2>Level 3 Authentication</h2>
      <p>Please record a video of yourself reading the following text:</p>
      <p>
        <strong>{textToRead}</strong>
      </p>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={(e) => setVideo(e.target.files[0])} />
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default Level3AuthPage;
