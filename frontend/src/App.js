import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Switch, Redirect } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ProductDetail from './pages/ProductDetail';
import Profile from './pages/Profile';
import Navbar from './components/Navbar';
import PrivateRoute from './components/PrivateRoute';
import { getUser } from './services/auth';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on app load
    const token = localStorage.getItem('token');
    if (token) {
      getUser()
        .then(data => {
          setUser(data);
          setLoading(false);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  return (
    <Router>
      <div className="app">
        <Navbar user={user} setUser={setUser} />
        
        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <Switch>
            <Route 
              path="/login" 
              render={(props) => 
                user ? <Redirect to="/dashboard" /> : <Login {...props} setUser={setUser} />
              } 
            />
            <Route 
              path="/register" 
              render={(props) => 
                user ? <Redirect to="/dashboard" /> : <Register {...props} setUser={setUser} />
              } 
            />
            <PrivateRoute path="/dashboard" component={Dashboard} user={user} />
            <PrivateRoute path="/product/:id" component={ProductDetail} user={user} />
            <PrivateRoute path="/profile" component={Profile} user={user} setUser={setUser} />
            <Route exact path="/">
              {user ? <Redirect to="/dashboard" /> : <Redirect to="/login" />}
            </Route>
          </Switch>
        )}
      </div>
    </Router>
  );
}

export default App; 