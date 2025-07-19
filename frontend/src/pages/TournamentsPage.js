import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TournamentsPage = () => {
  const [tournaments, setTournaments] = useState([]);

  useEffect(() => {
    const fetchTournaments = async () => {
      const { data } = await axios.get('/api/tournaments/');
      setTournaments(data);
    };

    fetchTournaments();
  }, []);

  return (
    <div>
      <h2>Tournaments</h2>
      <ul>
        {tournaments.map((tournament) => (
          <li key={tournament.id}>{tournament.name}</li>
        ))}
      </ul>
    </div>
  );
};

export default TournamentsPage;
