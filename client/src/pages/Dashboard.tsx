import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Spin, message, Typography } from 'antd';
import { 
  TrophyOutlined, 
  TeamOutlined, 
  BarChartOutlined, 
  CalendarOutlined 
} from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;

interface Stats {
  competitions: number;
  athletes: number;
  results: number;
  events: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/stats');
      setStats(response.data);
    } catch (error) {
      message.error('Failed to fetch statistics');
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <Title level={4} type="secondary">
        Welcome to the Athletics Data Management System
      </Title>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Competitions"
              value={stats?.competitions || 0}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Athletes"
              value={stats?.athletes || 0}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Results"
              value={stats?.results || 0}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Events"
              value={stats?.events || 0}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="System Overview" style={{ height: 300 }}>
            <div style={{ padding: '20px 0' }}>
              <p>
                This athletics data management system provides comprehensive access to 
                competition data, athlete information, and performance results.
              </p>
              <p>
                Use the navigation menu to explore:
              </p>
              <ul>
                <li><strong>Competitions:</strong> Browse all athletics competitions</li>
                <li><strong>Athletes:</strong> Search and view athlete profiles</li>
                <li><strong>Results:</strong> Access detailed competition results</li>
                <li><strong>Statistics:</strong> View comprehensive data analytics</li>
              </ul>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Recent Activity" style={{ height: 300 }}>
            <div style={{ padding: '20px 0' }}>
              <p>Database contains:</p>
              <ul>
                <li>{stats?.competitions || 0} competitions from around the world</li>
                <li>{stats?.athletes || 0} registered athletes</li>
                <li>{stats?.results || 0} performance results</li>
                <li>{stats?.events || 0} athletic events</li>
              </ul>
              <p style={{ marginTop: 20, fontStyle: 'italic', color: '#666' }}>
                Data is regularly updated and synchronized with official athletics databases.
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
