import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
} from '@material-ui/core';
import { makeStyles } from '@material-ui/core/styles';
import { getSimulationResults, getSimulations } from '../services/simulationService';

const useStyles = makeStyles((theme) => ({
  root: {
    flexGrow: 1,
    padding: theme.spacing(3),
  },
  card: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  cardContent: {
    flexGrow: 1,
  },
  chartContainer: {
    height: 400,
    marginTop: theme.spacing(2),
  },
  tableContainer: {
    marginTop: theme.spacing(2),
  },
  metricValue: {
    fontSize: '2rem',
    fontWeight: 'bold',
    color: theme.palette.primary.main,
  },
  metricLabel: {
    color: theme.palette.text.secondary,
  },
  loadingContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '400px',
  },
  errorContainer: {
    margin: theme.spacing(2),
  },
}));

function Dashboard() {
  const classes = useStyles();
  const [simulationResults, setSimulationResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get the most recent simulation
        const simulations = await getSimulations(1, 0);
        if (simulations && simulations.length > 0) {
          const latestSimulation = simulations[0];
          const results = await getSimulationResults(latestSimulation.id);
          setSimulationResults(results);
        }
      } catch (err) {
        setError('Failed to fetch simulation results. Please try again later.');
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className={classes.loadingContainer}>
        <CircularProgress />
      </div>
    );
  }

  if (error) {
    return (
      <div className={classes.errorContainer}>
        <Alert severity="error">{error}</Alert>
      </div>
    );
  }

  if (!simulationResults) {
    return (
      <div className={classes.errorContainer}>
        <Alert severity="info">No simulation results available.</Alert>
      </div>
    );
  }

  const { daily_results, summary } = simulationResults;

  // Prepare data for charts
  const chartData = Object.entries(daily_results).map(([date, data]) => ({
    date,
    balance: data.balance,
    profit_loss: data.profit_loss,
    trades_count: data.trades_count,
  }));

  return (
    <div className={classes.root}>
      <Grid container spacing={3}>
        {/* Summary Metrics */}
        <Grid item xs={12} md={3}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Initial Balance
              </Typography>
              <Typography className={classes.metricValue}>
                ${summary.initial_balance.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Final Balance
              </Typography>
              <Typography className={classes.metricValue}>
                ${summary.final_balance.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Total Trades
              </Typography>
              <Typography className={classes.metricValue}>
                {summary.total_trades}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Win Rate
              </Typography>
              <Typography className={classes.metricValue}>
                {(summary.win_rate * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Portfolio Value Chart */}
        <Grid item xs={12}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Portfolio Value Over Time
              </Typography>
              <div className={classes.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="balance"
                      stroke="#8884d8"
                      name="Portfolio Value"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </Grid>

        {/* Daily P&L Chart */}
        <Grid item xs={12}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Daily Profit/Loss
              </Typography>
              <div className={classes.chartContainer}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar
                      dataKey="profit_loss"
                      fill="#82ca9d"
                      name="Daily P&L"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </Grid>

        {/* Detailed Results Table */}
        <Grid item xs={12}>
          <Card className={classes.card}>
            <CardContent className={classes.cardContent}>
              <Typography variant="h6" gutterBottom>
                Detailed Results
              </Typography>
              <TableContainer component={Paper} className={classes.tableContainer}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell align="right">Balance</TableCell>
                      <TableCell align="right">Trades</TableCell>
                      <TableCell align="right">P&L</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {chartData.map((row) => (
                      <TableRow key={row.date}>
                        <TableCell component="th" scope="row">
                          {row.date}
                        </TableCell>
                        <TableCell align="right">
                          ${row.balance.toFixed(2)}
                        </TableCell>
                        <TableCell align="right">{row.trades_count}</TableCell>
                        <TableCell
                          align="right"
                          style={{
                            color: row.profit_loss >= 0 ? 'green' : 'red',
                          }}
                        >
                          ${row.profit_loss.toFixed(2)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
}

export default Dashboard; 